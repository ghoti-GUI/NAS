# -*-coding:Utf-8 -*
#!/usr/bin/env python3

import json


class network():
    def __init__(self, prefix, protocol, r1, r2, inter1, inter2):
        self.prefix = prefix
        self.protocol = protocol
        self.r1 = r1
        self.r2 = r2
        self.inter1 = inter1
        self.inter2 = inter2

def set_net(net, prefix, protocol, r1, r2, inter1, inter2):
    net1 = network(prefix, protocol, r1, r2, inter1, inter2)
    net.append(net1)


# to know how many routers we have
def get_nbr_rt(fic_intent):
    name_rts = []
    i = 1
    nbr_rt = 0
    while i<len(fic_intent):
        rt_ids = [fic_intent[i]["link_1"][0], fic_intent[i]["link_2"][0]]
        for rt_id in rt_ids:
            if rt_id not in name_rts:
                name_rts.append(rt_id)
                nbr_rt += 1
        i+=1
    return nbr_rt

# to get the AS number we have
def get_as(net):
    protocols = ["ospf", "bgp"]
    AS = []
    i = 0
    while i<len(net):
        protocol = net[i].protocol

        if protocol[0] in protocols and protocol not in AS:
            prefix = net[i].prefix
            prefix_2 = prefix.split('.')
            inAS = prefix_2[0]+"."+prefix_2[1]+".0."+prefix_2[3]
            protocol.append(inAS)

            AS.append(protocol)
        i+=1
    return AS

"""     get all names of routers    """
def get_routers_names(fic_intent):
    name_rts = []
    i = 1
    while i<len(fic_intent):
        name_rts_link = [fic_intent[i]["link_1"][0], fic_intent[i]["link_2"][0]]
        for rt in name_rts_link:
            if rt not in name_rts:
                name_rts.append(rt)
        i+=1
    return name_rts

"""     init all routers    """
def init_routers(fic_intent):
    routers = []
    name_rts = []
    i = 1
    while i<len(fic_intent):
        name_rts_link = [fic_intent[i]["link_1"][0], fic_intent[i]["link_2"][0]]
        AS_rt = fic_intent[i]["protocol"]

        for rt in name_rts_link:
            if rt not in name_rts:
                name_rts.append(rt)
                info_router = {
                    "AS" : AS_rt,
                    "name" : rt,
                    "border-router" : False,
                    "GNS3_file" : "",
                    "networks" : []
                }
                
                if rt[0:1] == "C":
                    info_router["AS"] = ["bgp", fic_intent[i]["link_1"][2]]

                routers.append(info_router)
        i+=1
    return routers, name_rts

"""     set "GEN3_file"     """
def set_chemins(fic_intent, routers):
    for router in routers:
        router_name = router["name"]
        if router_name[0:1] != "C":
            router["GNS3_file"] = fic_intent[0]["cfg_chemins"][router_name]
        


"""     set "border-router"     """
def set_border_router(fic_intent, routers):  
    border_routers = []
    i = 1
    #get all border_routers
    while i<len(fic_intent):
        if fic_intent[i]["protocol"][0] == "ebgp":
            border_routers_link = [fic_intent[i]["link_1"][0], fic_intent[i]["link_2"][0]]
            for border_router in border_routers_link:
                if border_router not in border_routers:
                    border_routers.append(border_router)
        i+=1
    #set "border-router"
    for router in routers:
        if router["name"] in border_routers:
            router["border-router"] = True

def get_mask(mask_32):
    mask_2 = "1" *mask_32
    mask_2 += "0" *(32-mask_32)
    mask_2_list = [mask_2[0: 8],mask_2[8: 16] ,mask_2[16: 24] ,mask_2[24: 32] ]
    mask_10 = [int(mask_2_list[0], 2),int(mask_2_list[1], 2) ,int(mask_2_list[2], 2) ,int(mask_2_list[3], 2) ]
    mask_fin = str(mask_10[0]) + "." + str(mask_10[1]) + "." + str(mask_10[2]) + "." + str(mask_10[3])
    return mask_fin

def get_ip(prefix, nbr):
    prefix = prefix.split("/")
    mask_32 = int(prefix[1])
    prefix = prefix[0].split(".")

    ip = prefix[0] + "." + prefix[1] + "." + prefix[2] + "." + str(int(prefix[3])+nbr)
    mask = get_mask(mask_32)
    return (ip + " " + mask)

"""     set network     """
def set_networks(fic_intent, routers, router_name):
    i = 1
    while i<len(fic_intent):
        for k in [1, 2]:
            k_neighbor = k%2+1
            if fic_intent[i][f"link_{k}"][0] == router_name:
                rt_connect = fic_intent[i][f"link_{k_neighbor}"][0]
                net = [
                    {
                        "name" : rt_connect,
                        "interface" : "GigabitEthernet" + fic_intent[i][f"link_{k}"][1][1:4]
                    }
                ]
                if rt_connect[0:1] == "C":
                    dic_add = {
                        "AS" : 0,
                        "VPN" : True,
                        "neighbor_ip" : "",
                        "ip" : ""
                    }

                    prefix = fic_intent[i]["prefix"]

                    id_rt = 0
                    while id_rt<len(routers):
                        if routers[id_rt]["name"] == rt_connect:
                            dic_add["AS"] = routers[id_rt]["AS"][1]
                            break
                        id_rt+=1
                    dic_add["neighbor_ip"] = get_ip(prefix, k)
                    dic_add["ip"] = get_ip(prefix, k_neighbor)
                    net[0].update(**dic_add)

                for router in routers:
                    if router["name"] == router_name:
                        router["networks"].append(net)
                        break
        i+=1

def pop_AS(routers):
    for router in routers:
        del router["AS"]

"""     get all router infomations   """
def get_routers(fic_intent):
    routers, name_rts = init_routers(fic_intent)
    set_chemins(fic_intent, routers)
    set_border_router(fic_intent, routers)
    for name_rt in name_rts:
        set_networks(fic_intent, routers, name_rt)
    
    return routers

def set_IP_version(info_AS):
    inAs = info_AS[0]["IP-range"]["physical"]["inAs"]
    if "." in inAs:
        info_AS[0]["IP-version"] = 4
    elif ":" in inAs:
        info_AS[0]["IP-version"] = 6


def translate(dir_link, dir_router):
    #init networks
    net = []
    intent = []


    with open(dir_link, 'r') as rt_file:
        intent = json.load(rt_file)
        nbr_rt = get_nbr_rt(intent)

        #set networks
        i = 1
        while i<len(intent):

            r1 = intent[i]["link_1"][0]
            r2 = intent[i]["link_2"][0]

            inter1 = intent[i]["link_1"][1]
            inter2 = intent[i]["link_2"][1]

            prefix = intent[i]["prefix"]
            protocol = intent[i]["protocol"]
            
            set_net(net, prefix, protocol, r1, r2, inter1, inter2)
            i+=1

        AS = get_as(net)

        #transform it into router.json
        with open(dir_router, "w") as intent_router:
            routers = get_routers(intent)

            routers_ospf = []
            routers_other = []
            for router in routers:
                if router["AS"][0] == "ospf":
                    routers_ospf.append(router)
                else:
                    routers_other.append(router)
            pop_AS(routers_ospf)
            pop_AS(routers_other)

            AS_precis = [
                {
                    "number" : int(AS[0][1]), 
                    "IP-version" : 0,
                    "IGP" : AS[0][0],
                    "BGP" : {
                        "iBGP" : "PE full-meshed",
                        "eBGP" : ""
                    },
                    "MPLS" : True,
                    "IP-range" : {
                        "physical" : {
                            "inAs" : AS[0][3],
                            "peering" :[""]
                        },
                        "loopback" : "192.168.0.X/32"
                    },

                    "routers" : []
                }
            ]

            set_IP_version(AS_precis)

            if AS_precis[0]["IGP"] == "ospf":
                AS_precis[0]["routers"] = routers_ospf

            info_precis = {"AS":AS_precis}
            json.dump(info_precis, intent_router, indent=4)
            print("load finished...")
