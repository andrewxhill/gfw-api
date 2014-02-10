# Gather, stitch, and crop map tiles 
# given a bounding box in world coordinates 
# and pixel width and height 

from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch 

import sys
import os
import io
import logging
import urllib
import urllib2
import webapp2
import math
import json

from google.appengine.api import images
from google.appengine.api import urlfetch
from google.appengine.api import memcache

import cache

if 'SERVER_SOFTWARE' in os.environ:
    PROD = not os.environ['SERVER_SOFTWARE'].startswith('Development')
else:
    PROD = True

maxzoom = 5

class BaseHandler(webapp2.RequestHandler):
    def render_template(self, f, template_args):
        path = os.path.join(os.path.dirname(__file__), "templates", f)
        self.response.out.write(template.render(path, template_args))

    def push_html(self, f):
        path = os.path.join(os.path.dirname(__file__), "html", f)
        self.response.out.write(open(path, 'r').read())



# Create a species range map.
#    params:
#        name - a valid scientific name
#        size - width,height in pixels
class StaticMap():
    def get(self, iso, width, height):
        self.iso = iso
        self.width = width
        self.height = height
        self.size = [width, height]
        if not self.probeCache():
            self.getStaticMap()
            
    def getStaticMap(self):
        # some constants, world dimensions in 
        # the web mercator projection (SRID:3857)
        height3857 = 39943738
        width3857 = 40075017
        xmin3857 = -20037508
        ymax3857 = 19971868
        #get bounds if none using extent from data
        self.bounds = None
                
        #get the desired map size in pixels
        
        #base tile URL (CF cached)    
        self.tileUrl = (""
            "https://wri-01.cartodb.com/"
            "tiles/layergroup/b5d66373b95dc2cd8a1e141d8d32314d:1391970773838.13/%i/%i/%i.png?%s")
   
        self.tileSql = "SELECT * FROM world_countries_pubsub(\'%s\')"
        
        #basemap tiles
        self.baseUrl = (""
            "http://c.tiles.mapbox.com/v3/examples.map-szwdot65/%i/%i/%i.png")
        
        self.sqlUrl = "https://wri-01.cartodb.com/api/v2/sql?%s"
        self.boundsSql = """
            SELECT 
                ST_XMIN(geom) as xmin,
                ST_YMIN(geom) as ymin,
                ST_XMAX(geom) as xmax, 
                ST_YMAX(geom) as ymax 
            FROM (
                SELECT 
                    ST_Buffer(ST_Extent(the_geom_webmercator),20000) as geom 
                FROM get_species_tile(\'%s\')
            ) tmp"""
        self.name = self.request.get("name",None)
        self.tilesDone = 0
        
        
        logging.info(self.boundsSql % (self.name))
        
        if self.bounds == None:
            bounds = urlfetch.fetch(
                self.sqlUrl % (
                    urllib.urlencode(
                        dict(q = self.boundsSql % (self.name)))), deadline=120)            
            if bounds.status_code == 200:
                logging.info(bounds.content)
                speciesBounds = json.loads(bounds.content)
                self.bounds = [
                    speciesBounds["rows"][0]["xmin"],
                    speciesBounds["rows"][0]["ymin"],
                    speciesBounds["rows"][0]["xmax"],
                    speciesBounds["rows"][0]["ymax"]]
            logging.info(bounds.content)
            
        #get the species extent in World Coordinates
        self.worldBounds = [
            256*math.fabs(self.bounds[0]-xmin3857)/width3857,
            256*math.fabs(self.bounds[1]-ymax3857)/height3857,
            256*math.fabs(self.bounds[2]-xmin3857)/width3857,
            256*math.fabs(self.bounds[3]-ymax3857)/height3857]

            
        #figure out the right zoom level 
        #first get the resolution of each side
        xRes = math.fabs((self.worldBounds[2]-self.worldBounds[0])/self.size[0])
        yRes = math.fabs((self.worldBounds[3]-self.worldBounds[1])/self.size[1])
        
        logging.info("xres: %f yres: %f" % (xRes,yRes))
        #pick the biggest one
        res = max(xRes,yRes)
        logging.info("res is %f" % (res))
        
        #figure out which zoom level will fit the largest resolution.
        zoom = math.floor(math.log((1/res),2))
        
        maxzoom = min(math.floor(self.size[1]/5),math.floor(self.size[0]/5))
        
        self.zoom = min(zoom,maxzoom)            


        logging.info('Zoom level is %i' % (self.zoom))
        
        #figure out the pixel bounds at the chosen zoom level
        self.pixelBounds = []
        for coord in self.worldBounds:
            self.pixelBounds.append(coord*math.pow(2,(int(self.zoom))))
            logging.info(
                "worldcoord: %f, pixcoord %f" % 
                (coord,coord*math.pow(2,(int(self.zoom)))))
        
        #blow out pixel coordinates to desired size
        self.dpX = self.pixelBounds[2]-self.pixelBounds[0]
        self.cX = (self.pixelBounds[2]+self.pixelBounds[0])/2
        self.dpY = self.pixelBounds[1]-self.pixelBounds[3]
        self.cY = (self.pixelBounds[1]+self.pixelBounds[3])/2
        #if (dpX)<self.size[0]:
        self.pixelBounds[0] = self.cX-(self.size[0]/2)
        self.pixelBounds[2] = self.cX+(self.size[0]/2)
        
        #if (dpY)<self.size[1]:
        self.pixelBounds[3] = self.cY-(self.size[1]/2)
        self.pixelBounds[1] = self.cY+(self.size[1]/2)
                                  
        
        
        
        #get the x and y tile cooridnates the pixel bounds intersects
        self.tileCoords = []
        for pix in self.pixelBounds:
            tileCoord = int(math.floor(pix/256))
            self.tileCoords.append(tileCoord)
            logging.info("tile: %i" %(int(math.floor(pix/256))))
        
        #reset size to the size in that zoom level
        
        logging.info(
             "Making a map sized %i wide by %i tall " % 
                (self.size[0],self.size[1]))
        
        #composite the tiles
        tiles = []
        
        Y = -1
        self.image = None
        self.rpcs = []
        self.tiles = {'base': {}, 'map': {}}
            
        self.tileWidth = self.tileCoords[2]+1 - self.tileCoords[0]
        self.tileHeight = self.tileCoords[1]+1 - self.tileCoords[3] 
        self.tilesRequested = self.tileWidth * self.tileHeight * 2 
        self.pixHeight = self.tileHeight * 256
        self.pixWidth = self.tileWidth * 256

        for tileY in range(self.tileCoords[3],self.tileCoords[1]+1):
            Y = Y + 1
            X = -1
            for tileX in range(self.tileCoords[0],self.tileCoords[2]+1):
                X = X + 1
                logging.info(
                     "appending tX: %i tY: %i X: %i Y: %i" % 
                     (tileX, tileY, X, Y))
                
                self.createTileRPC(tileX,tileY,X,Y)
        
        
        for rpc in self.rpcs:
            rpc.wait()
        
        
        self.cropComposite()        
        self.cacheImage()
        self.outputImage()

            
    def cropComposite(self):
        #crop to desired pixel size, centered on the bounds.
        left_x = float(
            (self.cX-self.size[0]/2-(self.tileCoords[0]*256))/self.pixWidth)
        top_y = float(
            (self.cY-self.size[1]/2-(self.tileCoords[3]*256))/self.pixHeight)
        right_x = float(
            1-(((self.tileCoords[2]+1)*256)-(self.cX+self.size[0]/2))/
                self.pixWidth)
        bottom_y = float(
             1-(((self.tileCoords[1]+1)*256)-(self.cY+self.size[1]/2))/
                self.pixHeight)
        self.image = images.crop(self.image, left_x, top_y, right_x, bottom_y)
        
    def create_callback(self,rpc,url,type,X,Y):
        return lambda: self.handle_result(rpc,url,type,X,Y)

    
    def createTileRPC(self, tileX, tileY, X, Y):
        
        tileUrl = self.getTileURL(tileX, tileY)
        baseTileUrl = self.getBaseTileURL(tileX, tileY)
        
        self.createRPC(self.getBaseTileURL(tileX, tileY), 'base', X, Y)
        self.createRPC(self.getTileURL(tileX, tileY), 'map', X, Y) 

    def createRPC(self, url, type, X, Y):
        
        result = memcache.get(url)
        if result:
            logging.info('Got %s %i %i from memcache' % (type, X, Y) )
            self.addResult(result, type, X, Y)
        else:
            result = cache.get(url,value_type = 'blob')
            if result:
                logging.info('Got %s %i %i from datastore' % (type, X, Y) )
                memcache.add(url,result)
                self.addResult(result, type, X, Y)
            else:
                logging.info('Getting %s %i %i from %s' % (type, X, Y, url) )
                rpc = urlfetch.create_rpc(deadline=240)
                rpc.callback = self.create_callback(rpc, url, type, X, Y)
                urlfetch.make_fetch_call(rpc,url)
                self.rpcs.append(rpc)
                
    def handle_result(self, rpc, url, type, X, Y):    
        
       result = rpc.get_result()
       try:
           if result.status_code == 200:
               logging.info('%s tile X:%i Y:%i made it' % (type, X, Y))
               self.addResult(result.content, type, X, Y)
               logging.info('caching url %s' % url)
               memcache.add(url, result.content)
               cache.add(url, result.content, value_type="blob")
        
       except:
           logging.info('%s tile X:%i Y:%i failed' % (type, X, Y))
           self.tilesDone = self.tilesDone + 1
        
    def cacheImage(self):
        memcache.add(self.request.url, self.image)
        cache.add(self.request.url, self.image,value_type="blob")
    
    def probeCache(self):  
        result = memcache.get(self.request.url)
        if result:
            logging.info('Got %s from memcache' % (self.request.url) )
            self.image = result
            self.outputImage()
            return True
        else:
            result = cache.get(self.request.url,value_type = 'blob')
            if result:
                logging.info('Got %s from datastore' % (self.request.url))      
                self.image = result
                self.outputImage()
                return True
            else:
                return False
        
    def addResult(self, result, type, X, Y):
    
        logging.info('type: %s ' % type)
        if not ( X in self.tiles[type]):
            self.tiles[type][X] = {}

        self.tiles[type][X][Y] = result
        
        self.tilesDone = self.tilesDone + 1
        
        if type == 'base':
            if self.image == None:
                self.image = result
            logging.info('compositing base %i %i' % (X, Y))
            self.image = images.composite(
                 [(self.image,0,0,1.0,images.TOP_LEFT),
                 (result, (X*256), (Y*256), 1.0, images.TOP_LEFT)],
                 self.pixWidth, self.pixHeight)
            if X in self.tiles['map']:
                if Y in self.tiles['map'][X]:
                    logging.info('compositing map %i %i' % (X, Y))
                    self.image = images.composite(
                     [(self.image,0,0,1.0,images.TOP_LEFT),
                     (self.tiles['map'][X][Y], (X*256), (Y*256), 0.55, 
                         images.TOP_LEFT)],
                     self.pixWidth, self.pixHeight)
            
        if type == 'map':
            if X in self.tiles['base']:
                if Y in self.tiles['base'][X]:
                    logging.info('compositing map %i %i' % (X, Y))
                    self.image = images.composite(
                     [(self.image,0,0,1.0,images.TOP_LEFT),
                     (result, (X*256), (Y*256), 0.55, images.TOP_LEFT)],
                     self.pixWidth, self.pixHeight)
            
                
        logging.info(
             '%i tiles done, %i tiles requested' % 
             (self.tilesDone, self.tilesRequested))
            
    def fixTileX(self,tx):
        if tx<0:
            while tx<0:
                tx=int(math.pow(2,self.zoom)+tx)
            logging.info("changed X %i" % tx)
        
        if (tx>=math.pow(2,self.zoom)):
            while tx>=math.pow(2,self.zoom):
                tx=tx-math.pow(2,self.zoom)
            #tx=tx-1
        return tx

    def fixTileY(self,ty):
        if ty < -1:
            return -1
        elif (ty>math.pow(2,self.zoom)):
            return int(math.pow(2,self.zoom))
        else:
            return ty
        
    
    def getTileURL(self,x,y):
        x = self.fixTileX(x)
        y = self.fixTileY(y)
        url = self.tileUrl % (
            self.zoom,
            x,y,(urllib.urlencode(dict(sql=(self.tileSql % (self.name))))))
        logging.info(url)
        return url
            
    def getBaseTileURL(self,X,Y):
        
        X = self.fixTileX(X)
        
        #if in the artic, use a blue base tile
        if(Y<0):
            url = self.baseUrl % (8,0,0)
        else:
            Y = self.fixTileY(Y)
            url = self.baseUrl % (self.zoom,X,Y)
        logging.info(url)    
        return url
    
    def outputImage(self):
        #write image to client
        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(self.image)

         
application = webapp2.WSGIApplication(
         [('/map', StaticMap)],
         debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()