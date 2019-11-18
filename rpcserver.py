from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
from multiprocessing import Process, Lock, Pool
from socketserver import ThreadingMixIn
import xmlrpc.client
import sys
import urllib.request #this library used to get public IP of current machine
import time
import random
import queue
import time
import threading
import sys, traceback
import math #for floor


msg_list = queue.Queue() #list of all messages we want to send or waiting for recving it
nodes_list = [] #list of all nodes we are connected to, including this node
HASH_TABLE_SIZE = 2**10 #the hash table size is 1024 at first but as it gets bigger, the size will increase
Bucket = list([None]*HASH_TABLE_SIZE)#Define a bucket for current server
#less lock (1/4) than hash table size
strip_scale = 4
Bucket_lock = [threading.Lock() for _ in range(math.floor(HASH_TABLE_SIZE/strip_scale))]
NODE_NUMBER = 3#define number of nodes

#initialize current node
external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')#get my public id
my_key = random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*3) #generate a key
my_value = external_ip #value = public ip
tl = [] 
tl.append([my_key,my_value]) 
Bucket[hash(my_key)%HASH_TABLE_SIZE] = tl #add key,value to the its place
print('I started with public IP ',external_ip)
nodes_list.append([external_ip,str(my_key)])

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class SimpleThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


#def server_func(msg_list):
def server_func():
    # Create server
    #server = SimpleXMLRPCServer(("0.0.0.0", 8000),
    #                        requestHandler=RequestHandler,logRequests=False)
    server = SimpleThreadedXMLRPCServer(("0.0.0.0", 8000),logRequests=False)
    server.register_introspection_functions()

    #register function
    server.register_function(realget,'realget')
    server.register_function(getkey,'getkey')
    server.register_function(realput,'realput')
    #server.register_instance(MyFuncs())
    # Run the server's main loop
    server.serve_forever()

#########################Server implemented function#############################

#this function just return current node key
def getkey():
    return my_key


def realget(key):
    try:
        #lck = Lock() #lock in order to write msg_list
        #lck.acquire()
        #if it is locked already, return FAILED
        lock_location = hash(key)%(HASH_TABLE_SIZE/strip_scale) #get the scaled lock_location
        if(Bucket_lock[lock_location].locked()):
            return 'FAILED'
        Bucket_lock[lock_location].acquire() #lock it !
        ls = Bucket[lock_location] #get list of that key-index
        if(ls==None): #there is no key there
            #lck.release()
            Bucket_lock[lock_location].release()
            return 'NOBUCKET'
        else: #search for this key
            for items in ls:#check the key
                if(items[0] == (key)):
                    #lck.release()
                    Bucket_lock[lock_location].release()
                    return str(items[1])
            Bucket_lock[lock_location].release()
            return 'NOKEY' #otherwise return the false for key
    except Exception as ex:
        print(ex,'------------------------------------')
        traceback.print_exc(file=sys.stdout)
        Bucket_lock[lock_location].release()
        return 'FAILED'

def realput(key,val,msg):
    lock_location = hash(key)%(HASH_TABLE_SIZE/strip_scale) #get the scaled lock_location
    #in prepare part just lock the key
    if(msg=='PREPARE'):
        if(Bucket_lock[lock_location].locked()):
            return 'NOTREADY'
        else: #lock the index
            Bucket_lock[lock_location].acquire() #lock it !
            return 'READY'
    if(msg=='ABORT'):
        if(Bucket_lock[lock_location].locked()):
            Bucket_lock[lock_location].release()
    if(msg=='COMMIT'): #save it and return DONE or FAILED
        try:
            ls = Bucket[lock_location] #get list of that key-index
            if(ls==None): #there is no key there
                ls = []
                ls.append([key,val])
                Bucket[lock_location] = ls
                Bucket_lock[lock_location].release()
                return 'DONE'
            else: #search for this key
                for i in range(len(ls)):#check the key
                    items = ls[i]
                    if(items[0] == int(key)):
                        items[1] = val
                        ls[i] = items
                        Bucket[lock_location] = ls
                        Bucket_lock[lock_location].release()
                        return 'DONE'
                ls.append([key,val])
                Bucket[lock_location] = ls
                Bucket_lock[lock_location].release()
                return 'DONE'
        except Exception as ex:
            print(ex,'------------------------------------')
            traceback.print_exc(file=sys.stdout)
            Bucket_lock[lock_location].release()
            return 'FAILED'

    ## dont forget to unlock



#in this function we search for closest node to send the data
def find_node(key,ndoes_list):
    min = HASH_TABLE_SIZE**3#a big number for minimum value
    #search for smallest distance to current key btwn nodes
    print('find node func:', nodes_list,key)
    for ns in nodes_list:
        if(abs(int(ns[1])-int(key))<min): 
            min = abs(int(ns[1])-int(key))
            res = ns
    return res


#get nodes list
#get list of all other nodes using text file
file = open('server_nodes.txt', 'r')  #read the address file
#add nodes address to nodes_list without a key for now
sservers = []
for lines in file:
    result = lines.find('\n') #remove \n if ther is any
    if(result>-1):
        lines = lines[0:result]
    if(external_ip != lines):
        #nodes_list.append([None,lines])
        #creat one message and push it in msg_list for later sending
        msg_list.put('connect'+','+external_ip+','+lines+','+str(hash(my_key))+','+str(my_value))
        sservers.append(lines)
        print(lines)





server_func()





