#!/usr/bin/env python

# if you want to run the tests outside of Travis (aka local linux box):
# 1) populate a fresh bash shell with the necessary env variables:
#    $>base/scripts/setupTravisEnv.sh
# 2) run the tests:
#    $>CROPS_CODI_PORT="tcp://172.17.0.11:10000" PYTHONPATH=$PYTHONPATH:`pwd`/base/tests/unit/ python tests.py
#    the CROPS_CODI_PORT is whatever ip address docker uses for linked containers. You check it by
#     running a linked container and doing a printenv
#    the tests utils are in base so I find it easiest to extend my pythonpath for those.

import unittest
import os
import subprocess
import shutil
import tempfile
import sys
import stat
import imp
import inspect
from utils.testutils import *
import time
import requests

TtoA={'core2-64':'x86_64',
      'i586':'i586',
      'aarch64':'aarch64',
      'armv5e':'arm',
      'mips64':'mips64'}

def startTargetToolchain(name):

    cmd = "docker  run -d -v /var/run/docker.sock:/var/run/docker.sock --link crops-codi   %s" % \
          (name)
    p=subprocess.Popen(cmd.split(), shell=False)

class TestToolchainsRegistered(unittest.TestCase):
    def setUp(self):
        self.codiAddr = os.environ['CODI_ADDR']
        self.codiPort=os.environ['CODI_PORT']
        self.dockerhubRepo=os.environ['DOCKERHUB_REPO']
        self.ypRelease=os.environ['YP_RELEASE']
        cmd = "docker  run -d -v /var/run/docker.sock:/var/run/docker.sock -p %s:%s  --name=crops-codi %s/codi" % \
              (self.codiPort,self.codiPort,self.dockerhubRepo)
        p=subprocess.Popen(cmd.split(), shell=False)
        # getting rethinkdb and codi up can take a bit
        time.sleep(10)
        self.targets = os.environ['TARGETS']
        self.toolchainContainers=[]
        for t in self.targets.split():
            toolchainContainer="%s/toolchain-%s:%s" % (self.dockerhubRepo,t,self.ypRelease)
            self.toolchainContainers.append(toolchainContainer)
            startTargetToolchain(toolchainContainer)
        # we need to give the containers time to register
        time.sleep(10)
    def tearDown(self):
        #remove the server container
        cmd = "docker rm -f crops-codi"
        #p=subprocess.Popen(cmd.split(), shell=False)
        pass


    def test_toolchains_registered(self):
        found=True
        for t in self.targets.split():
            time.sleep(1)
            myFilter={'filter':'{\"target\":{\"arch\":\"%s\"}}'%(TtoA[t])}
            myUrl = "http://%s:%s/codi/list-toolchains"%(self.codiAddr,self.codiPort)
            r=requests.get(myUrl,params=myFilter)
            myFound=(r.status_code==200)
            found &= myFound
            if not myFound:
                print("Bad status code %d from: %s"%(r.status_code,r.url))
                continue
            try:
                j=r.json()[0]
                myFound = TtoA[t] in j['target']['arch']
            except:
                myFound=False
            if not myFound:
                print("Bad arch. Failed to find arch toolchain :%s\n"%(TtoA[t]))
                print ("BAVERY: rText=%s\n"%(r.text))
                if len(r.json()) > 0:
                    print ("returned json was %s\n"%(r.json()[0]))
                print("from CODI server url=<%s>,filter=<%s>\n"%(myUrl,myFilter))

            found &= myFound


        self.assertTrue(found)



if __name__ == '__main__':
    unittest.main()