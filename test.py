from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
from multiprocessing import Process, Lock
import xmlrpc.client
import sys
import urllib.request #this library used to get public IP of current machine
import time
import random
import queue
from multiprocessing import Pool
import statistics 
import threading


def print_test(i):
    print(i,' second')
    for j in range(5):
        print(i+j)

if __name__ == '__main__':
    proc = []
    for i in range(0,8):
        msg_list =[]
        n = random.randint(-11000,11000)
        print(n,' first')
        p = Process(target=print_test, args=(n,))
        #p = threading.Thread(target=print_test, args=(n,)) 
        p.start()
        proc.append(p)
    for p in proc:
        p.join()