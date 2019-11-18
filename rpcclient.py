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


#msg_list = queue.Queue() #list of all messages we want to send or waiting for recving it
msg_list = []
nodes_list = [] #list of all nodes we are connected to, including this node
HASH_TABLE_SIZE = 2**10 #the hash table size is 1024 at first but as it gets bigger, the size will increase
Bucket = list([None]*HASH_TABLE_SIZE)#Define a bucket for current server
NODE_NUMBER = 4#define number of nodes

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



def client_func(msg_list):
    #nodes_list = []
    #lck = Lock() #lock in order to write msg_list
    #f = open('client-log','a+') #open the log file
    pos_throuput = 0
    neg_throuput = 0
    latency = []
    while (len(msg_list)>0):#not msg_list.empty()):#True:
        try:
            temp_msg = []#to save a backup
            #if(len(msg_list)>0):
            if(len(msg_list)>0):#not msg_list.empty()):
                #lck.acquire()
                res = []
                msgq = msg_list.pop(0) #msg_list.get() #select queue front
                temp_msg = msgq
                #extract message 
                msg = msgq.split(',')
                mtype = msg[0]; sndr = msg[1]; recvr = msg[2]; ki = msg[3]; val = msg[4]
                #write into log file what you are about to do
                #if(f.closed()):
                #    f = open('client-log','a+') #open the log file
                #f.write("\n%s" % msgq)
                if(mtype=='get'): #process it for get
                    s = xmlrpc.client.ServerProxy('http://'+nodes_list[0][0]+':8000') #send message to the recevr
                    t1 = time.time()
                    res = s.get(ki,external_ip)#fidn recvr, add recvr and send it
                    t2 = time.time()
                    latency.append(t2-t1)
                    #chek the final result and print it
                    print('GET: ',res)
                    if(res == 'FAILED'): #push back current message for later call
                        msg_list.insert(0,msgq)
                        neg_throuput = neg_throuput + 1
                        #f.write('++')
                    elif(res == 'NOKEY' or res == 'NOBUCKET' ):
                        print('This key is not existed!')
                        pos_throuput = pos_throuput + 1
                        #f.write('--')
                    else:
                        print(res)
                        pos_throuput = pos_throuput + 1
                        
                        #f.write('--')
                if(mtype=='put'):
                    s = xmlrpc.client.ServerProxy('http://'+nodes_list[0][0]+':8000') #send message to the recevr
                    t1 = time.time()
                    res = s.put(ki,val,external_ip)#fidn recvr, add recvr and send it
                    t2 = time.time()
                    latency.append(t2-t1)
                    print('PUT: ',res)
                    pos_throuput = pos_throuput + 1
                        #f.write('++')
                if(mtype == 'mput'):
                    s = xmlrpc.client.ServerProxy('http://'+nodes_list[0][0]+':8000') #send message to the recevr
                    t1 = time.time()
                    res = s.mput(msgq)#fidn recvr, add recvr and send it
                    t2 = time.time()
                    latency.append(t2-t1)
                    print('MULTI-PUT: ',res)
                    pos_throuput = pos_throuput + 1
                #f.close()    
        except Exception as ex:
            msg_list.insert(0,msgq)
            neg_throuput = neg_throuput + 1
            # if(not f.closed()):
            #     f.write('--')
            #     f.close()
            #msg_list.put(temp_msg) #restore the backup
            if(ex==KeyboardInterrupt):
                exit()
    #print('thorughput: ',pos_throuput/(pos_throuput+neg_throuput))
    #print('latency: ',statistics.mean(latency))
    f = open('results','a+')
    f.write(str(str(pos_throuput/(pos_throuput+neg_throuput))+','+str(statistics.mean(latency))+'\n'))
    f.close()
    #f.close() #close the log file


#this function recv number of request and generate keys and values for each item, then added it to the list
def hash_test(msg_list):    
    req_num = 10
    msg_list.append('get'+','+external_ip+',None,'+str(1111)+','+str(random.randint(0,10000)))
    msg_list.append('put'+','+external_ip+',None,'+str(1111)+','+str(random.randint(0,10000)))
    msg_list.append('get'+','+external_ip+',None,'+str(1111)+','+str(random.randint(0,10000)))
    for i in range(req_num):
        msg_list.append('put'+','+external_ip+',None,'+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str(random.randint(0,10000)))
        msg_list.append(str('mput'+','+external_ip+',None,'+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str(random.randint(0,10000))+
                            ','+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str(random.randint(0,10000))+
                            ','+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str(random.randint(0,10000))))
        msg_list.append('get'+','+external_ip+',None,'+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str('NONE'))
        msg_list.append('get'+','+external_ip+',None,'+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str('NONE'))
        msg_list.append('get'+','+external_ip+',None,'+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str('NONE'))
        #if(i%5==0):
            #msg_list.append(str('mput'+','+external_ip+',None,'+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str(random.randint(0,10000))+
             #               ','+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str(random.randint(0,10000))+
              #              ','+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str(random.randint(0,10000))))
    for i in range(req_num):
        msg_list.append('get'+','+external_ip+',None,'+str(random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*5))+','+str('NONE'))
    



#get nodes list
#get list of all other nodes using text file
print('coordinator address:')
file = open('co_node.txt', 'r')  #read the address file
#add nodes address to nodes_list without a key for now
for lines in file:
    result = lines.find('\n') #remove \n if ther is any
    if(result>-1):
        lines = lines[0:result]
    #creat one message and push it in msg_list for later sending
    #msg_list.append('connect'+','+external_ip+','+lines+','+str(hash(my_key))+','+str(my_value))
    print(lines)


#hash_test(msg_list)
#print(len(msg_list))#.qsize())
#client_func(msg_list)


# s = xmlrpc.client.ServerProxy('http://128.180.110.48:8000') #send message to the recevr
# #print('sending key to target: ',target_node[0])
# res = s.get(22)#fidn recvr, add recvr and send it

if __name__ == '__main__':
    proc = []
    for i in range(0,8):
        msg_list =[]
        hash_test(msg_list)
        print(len(msg_list))
        client_func(msg_list)
        p = Process(target=client_func, args=(msg_list,))
        p.start()
        proc.append(p)
    for p in proc:
        p.join()






