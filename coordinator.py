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
from operator import itemgetter 


msg_list = queue.Queue() #list of all messages we want to send or waiting for recving it
nodes_list = [] #list of all nodes we are connected to, including this node
HASH_TABLE_SIZE = 2**10 #the hash table size is 1024 at first but as it gets bigger, the size will increase
Bucket = list([None]*HASH_TABLE_SIZE)#Define a bucket for current server
throughput = []#Define a bucket for current server
NODE_NUMBER = 3#define number of nodes
REPLICA_NUMBER = 2
NODE_NUMBER_WE_FOUND = 0
localsss = True
sorted_nodes = []
sorted_keys = []
server_keys = []


#initialize current node
external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')#get my public id
my_key = random.randint(0,HASH_TABLE_SIZE*NODE_NUMBER*3) #generate a key
my_value = external_ip #value = public ip
tl = [] 
tl.append([my_key,my_value]) 
Bucket[hash(my_key)%HASH_TABLE_SIZE] = tl #add key,value to the its place
print('I started with public IP ',external_ip)
nodes_list.append([external_ip,str(my_key)])
print(my_key)

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
    server.register_function(conn,'conn')
    server.register_function(get,'get')
    server.register_function(put,'put')
    server.register_function(mput,'mput')
    #server.register_instance(MyFuncs())
    # Run the server's main loop
    server.serve_forever()

#########################Server implemented function#############################

###conn function is deleted and we don't want to check if we are connected or not since in RPC we can directly access or be denied
def conn(msg):
    msg = msg.split(','); mtype = msg[0]; sndr = msg[1]; recvr = msg[2]; ki = msg[3]; val = msg[4]
    #lck = Lock() #lock in order to write msg_list
    #add this(sender) node to your node_list if it is not added, with hash key associated with that 
    # + send a welcome message to that node
    try:
        if(nodes_list.index([sndr,ki])<0): #if this node was not added before
            print('Hey '+ sndr + ' added you for sure!')
            return recvr+','+str(my_key)#'Hey '+ recvr + ' I added you before!!!...Welcome'
    except ValueError:
        0 #do nothing
    nodes_list.append([sndr,ki])
    print('Hey '+ sndr + ' added you')
    return recvr+','+str(my_key)#'Hey '+ recvr + ' I added you!...Welcome'


def get(key,sender):
    #open log file and record latest message
    #fff = open('coord-log','a+') #open the log file
    #fff.write("\n%s" % str(sender+','+key+',get'))

    if(len(server_keys) < len(sservers)): #check all servers and store their keys
        counter = 0
        #server_keys = []
        while(len(sservers)>counter):
            target_server = sservers[counter]
            try:
                s = xmlrpc.client.ServerProxy('http://'+target_server+':8000') #get server key
                ki = s.getkey()
                throughput.append([target_server,time.time()])
                server_keys.append(ki)
                counter = counter + 1
            except Exception as ex:
                print(ex)
                traceback.print_exc(file=sys.stdout)
        #sort the key for easier access
        #sorting nodes based on their keys
        sorted_indices = sorted(range(len(server_keys)),key=server_keys.__getitem__)
        sn = itemgetter(*sorted_indices)(sservers)
        sk = itemgetter(*sorted_indices)(server_keys)
        for i in range(len(sn)):
            sorted_nodes.append(sn[i])
            sorted_keys.append(sk[i])
    if(len(server_keys) < len(sservers)):
        #fff.write("--")
        #fff.close()
        return 'FAILED'
                
    #s = xmlrpc.client.ServerProxy('http://'+target_node[0]+':8000') #send message to the recevr
    res = []
    try:
        res = find_node(key,sorted_nodes,sorted_keys) #find target node
    except Exception as ex:
        print(ex)
        traceback.print_exc(file=sys.stdout)

    #send message to servers and ask for get///no response --> send failed!
    counter = 0
    for node in res:
        try:
            s = xmlrpc.client.ServerProxy('http://'+node+':8000') #get server key
            final_result = s.realget(key)
            throughput.append([node,time.time()])
            counter = counter+1
            #print(final_result)
            if((final_result == 'NOBUCKET' or final_result == 'FAILED' or final_result == 'NOKEY' )
                and (counter<len(res))): #if this node can't find it, use other node result
                continue
            #f.write("++")
            #f.close()
            return final_result
        except:
            0#do nothing
    #fff.write("--")
    #fff.close()
    return 'FAILED'

def put(key,val,sender):
    #open log file and record latest message
    #fff = open('coord-log','a+') #open the log file
    #fff.write("\n%s" % str(sender+','+key+',put'))

    #find nodes to send put
    target_nodes = []
    try:
        target_nodes = find_node(key,sorted_nodes,sorted_keys) #find target node
    except Exception as ex:
        print(ex)
        traceback.print_exc(file=sys.stdout)


    #in this loop we check if the the put is unsuccessful, then we add exponential
    time_to_sleep = 0.001 #a small number to sleep for

    while(True):
        #start 2P prepare/commit_abort
        #send message to servers and ask for put///no response --> send failed!
        ###1-Prepare Phase
        counter = 0
        #nn = random.randint(0,10000)
        for node in target_nodes:
            try:
                s = xmlrpc.client.ServerProxy('http://'+node+':8000') #get server key
                final_result = s.realput(key,val,'PREPARE')
                throughput.append([node,time.time()])
                if(final_result == 'READY'): #if this node locked the index count it
                    counter = counter+1
                if(final_result == 'NOTREADY'): #otherwise, send abort to all other nodes
                    break #finish the for if one node is not ready to lock
            except:
                break #finish the for if one node is not responsible
                0#do nothing
        #fff.write("\n%s" % str(final_result))
        #if after there are less than desired node ready for put, then abort
        if(counter < len(target_nodes)):
            for node in target_nodes:
                try:
                    s = xmlrpc.client.ServerProxy('http://'+node+':8000') #get server key
                    final_result = s.realput(key,val,'ABORT') #just send abort
                    throughput.append([node,time.time()])
                except:
                    0#do nothing
        else: #otherwise send commit
            counter = 0
            for node in target_nodes:
                try:
                    s = xmlrpc.client.ServerProxy('http://'+node+':8000') #get server key
                    final_result = s.realput(key,val,'COMMIT') #just send COMMIT
                    throughput.append([node,time.time()])
                    if(final_result == 'DONE'): #if this node locked the index count it
                        counter = counter+1
                except:
                    0#do nothing
        
    #check if the counter is 0, that mean we have to retry, otherwise we can return successful/semisuccesful
        if(counter > 0):
            break
        else: #other wise sleep and double the sleep time
            time.sleep(time_to_sleep)
            time_to_sleep = time_to_sleep * 2



    if(counter==len(target_nodes)):
        #fff.write('++')
        return 'SUCCESSFULPUT'
    elif(counter>0):
        #fff.write('++')
        return 'SEMISUCCESSFULPUT'
    

def mput(msgs):
    msg = msgs.split(',') #split the message
    mtype = msg[0]; sndr = msg[1]; recvr = msg[2]; 
    kis = msg[3:len(msg):2]; vals = msg[4:len(msg):2]

    #open log file and record latest message
    #fff = open('coord-log','a+') #open the log file
    #fff.write(msgs)
    

    #find nodes to send put
    target_nodes = []
    try:
        for i in range(len(kis)):
            target_nodes.append(find_node(kis[i],sorted_nodes,sorted_keys)) #find target node
    except Exception as ex:
        print(ex)
        traceback.print_exc(file=sys.stdout)



    #in this loop we check if the the put is unsuccessful, then we add exponential
    time_to_sleep = 0.001 #a small number to sleep for

    while(True):
        #start 2P prepare/commit_abort
        #send message to servers and ask for put///no response --> send failed!
        ###1-Prepare Phase
        counter = 0
        break_all = False
        for i in range(len(target_nodes)):
            nodes = target_nodes[i]
            for j in range(0,len(nodes)):
                node  = nodes[j]
                #print(node,j)
                try:
                    s = xmlrpc.client.ServerProxy('http://'+node+':8000') #get server key
                    final_result = s.realput(kis[i],vals[i],'PREPARE')
                    throughput.append([node,time.time()])
                    #print('mput: ',final_result)
                    if(final_result == 'READY'): #if this node locked the index count it
                        counter = counter+1
                    if(final_result == 'NOTREADY'): #otherwise, send abort to all other nodes
                        break_all = True #don't continue and break to outside loop too
                        break #finish the for if one node is not ready to lock
                except Exception as ex:
                    print(ex)
                    traceback.print_exc(file=sys.stdout)
                    break #finish the for if one node is not responsible
                    0#do nothing
            if(break_all):#break and don't continue
                break
        #fff.write("\n%s" % str(final_result))
        #if after there are less than desired node ready for put, then abort
        if(counter < len(target_nodes)*len(target_nodes[0])):
            for i in range(len(target_nodes)):
                nodes = target_nodes[i]
                for j in range(0,len(nodes)):
                    node  = nodes[j]
                    try:
                        s = xmlrpc.client.ServerProxy('http://'+node+':8000') #get server key
                        final_result = s.realput(kis[i],vals[i],'ABORT') #just send abort
                        throughput.append([node,time.time()])
                    except:
                        0#do nothing
        else: #otherwise send commit
            counter = 0
            for i in range(len(target_nodes)):
                nodes = target_nodes[i]
                for j in range(0,len(nodes)):
                    node  = nodes[j]
                    try:
                        s = xmlrpc.client.ServerProxy('http://'+node+':8000') #get server key
                        final_result = s.realput(kis[i],vals[i],'COMMIT') #just send COMMIT
                        throughput.append([node,time.time()])
                        if(final_result == 'DONE'): #if this node locked the index count it
                            counter = counter+1
                    except:
                        0#do nothing

        #check if the counter is 0, that mean we have to retry, otherwise we can return successful/semisuccesful
        if(counter > 0):
            break
        else: #other wise sleep and double the sleep time
            time.sleep(time_to_sleep)
            time_to_sleep = time_to_sleep * 2


    if(counter==len(target_nodes)*len(target_nodes[0])):
        #fff.write('++')
        return 'SUCCESSFULPUT'
    elif(counter>0):
        #fff.write('++')
        return 'SEMISUCCESSFULPUT'



#in this function we search for closest node to send the data
##The nodes and key of that nodes are sorted
def find_node(key,nodes,key_list):
    min = HASH_TABLE_SIZE**3#a big number for minimum value
    #search for smallest distance to current key btwn nodes
    #print('find node func:', nodes_list,key)
    for i in range(len(nodes)):
        ns = key_list[i]
        if(abs(int(ns)-int(key))<min): 
            min = abs(int(ns)-int(key))
            res = i #save the index
    target_nodes = []

    for i in (0,REPLICA_NUMBER-1):
        target_nodes.append(nodes[(res+i)%len(nodes)])
    return target_nodes





#get nodes list
#get list of all other nodes using text file
server_file = open('server_nodes.txt', 'r')  #read the address file


#add nodes address to server_list without a key for now
print('list of nodes')
sservers = []
for lines in server_file:
    result = lines.find('\n') #remove \n if ther is any
    if(result>-1):
        lines = lines[0:result]
    #if(external_ip != lines):
    #    msg_list.put('connect'+','+external_ip+','+lines+','+str(hash(my_key))+','+str(my_value))
    sservers.append(lines)
    print(lines)




def print_sth(s):
    print(s)
    a = time.time()
    while(True):
        if(time.time() - a >10):
            print(time.time())
            a = time.time()


#t1 = threading.Thread(target=print_sth, args=(10,)) 
#t1.start()
#t1.join()
try:
    server_func()
except KeyboardInterrupt as ex:
    print(len(throughput))
    ff = open('throughput','a+') #open the log file\
    for item in throughput:
        ff.write("\n%s" % str(str(item[0])+','+str(item[1])))
    ff.close()
    print('sth')


