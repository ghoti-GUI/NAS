import os

from intents_util import *

DATA_DIR = "./data"
CONFIG_MODEL_DIR = f"{DATA_DIR}/config_model"
INTENTS_DIR = f"{DATA_DIR}/intents_files"
OUTPUT_DIR = "./output"
CONFIG_DIR = f"{OUTPUT_DIR}/config"
JSON_DIR = f"{OUTPUT_DIR}/json"

FINAL_INTENTS_FILE = f"{JSON_DIR}/final_intents.json"
CONFIG_MODEL_END = f"{CONFIG_MODEL_DIR}/default_conf_end.txt"

OSPF_PROCESS_ID = 100


def init_config_file(nb_routers, intents):
    """Creates configuration files with hostname configuration."""
    # Creates the output directory
    try:
        os.mkdir(OUTPUT_DIR)
        os.mkdir(CONFIG_DIR)
        os.mkdir(JSON_DIR)
    except OSError:
        print(f"NOTE: {OUTPUT_DIR}, {CONFIG_DIR}, {JSON_DIR} already exist.\n")

    # Creates configuration files and writes hostname configuration
    hostnames = []
    for AS in intents["AS"]:
        for router in AS["routers"]:
            hostnames.append(router["name"])
    
    config_files = []
    for i in range(0, nb_routers):
        file_name = f"i{i+1}_startup-config.cfg"
        config_files.append(open(f"{CONFIG_DIR}/{file_name}", "w"))
        config_files[i].write(f"hostname {hostnames[i]}\n!\n")

    return config_files

def finish_config_file(conf_files_tab):
    """Writes last lines of default configuration and close each configuration file."""
    with open(CONFIG_MODEL_END, "r") as default_conf:
        for conf_file in conf_files_tab:
            conf_file.write(default_conf.read())
            conf_file.close()
            default_conf.seek(0) # Puts the file's pointer at the beginning


def write_interface_conf(conf_files, ip_matrix, links, intents):
    """
    Writes configuration of each interface for each router.

            Parameters:
                    conf_files (array of file objects): Array of configuration files
                    ip_matrix (2D matrix of strings): M[i][j] is the IP address of router i connected to router j
                    links (2D matrix of integers): L[i][j] is 1 if routers i and j are connected, 2 if they are border routers, 0 otherwise
                    intents (dictionary): contains configuration requirements for the network
    """
    # Writes configuration of interfaces for each router
    for AS in intents["AS"]:
        loopback_range = AS["IP-range"]["loopback"]
        IPv4 = (AS["IP-version"] == 4)
        IGP = AS["IGP"].lower()
        MPLS = AS["MPLS"]
        
        for router in AS["routers"]:
            ## Configuration of loopback address
            router["loopback"] = loopback_range.replace("X", str(router["index"] + 1))
            loopback_ip, loopback_mask = router["loopback"].split('/')

            conf_files[router["index"]].write("interface Loopback0\n")
            if (IPv4):
                loopback_mask = get_netmask(loopback_mask)
                conf_files[router["index"]].write(f" ip address {loopback_ip} {loopback_mask}\n")
                if (IGP == "ospf"):
                    conf_files[router["index"]].write(f" ip ospf {OSPF_PROCESS_ID} area 0\n")
            else: # IPv6
                conf_files[router["index"]].write(" no ip address\n")
                conf_files[router["index"]].write(f" ipv6 address {loopback_ip}/{loopback_mask}\n")
                conf_files[router["index"]].write(" ipv6 enable\n")
                if (IGP == "ospf"):
                    conf_files[router["index"]].write(" ipv6 ospf " + str(router["index"] + 1) + "00 area 0\n")
            conf_files[router["index"]].write("!\n")

            ## Configuration of physical interfaces
            for network in router["networks"]:
                for neighbor in network:
                    _, neighbor_router = find_router(neighbor["name"], intents)
                    if (neighbor_router != None): # Known neighbor = in the intents file
                        neighbor["ip"] = ip_matrix[router["index"]][neighbor_router["index"]]
                        conf_files[router["index"]].write("interface " + neighbor["interface"] + '\n')
                        if (IPv4):
                            conf_files[router["index"]].write(" ip address " + neighbor["ip"] + '\n')
                            if (IGP == "ospf"):
                                conf_files[router["index"]].write(f" ip ospf {OSPF_PROCESS_ID} area 0\n")
                            if (MPLS):
                                conf_files[router["index"]].write(" mpls ip\n")
                    else: # Unknown neighbor, i.e. a client
                        if ("VPN" in neighbor):
                            # Creation of VRF (we suppose that one VPN client = one VRF)
                            if not ("vrf" in neighbor):
                                neighbor["vrf"] = str(neighbor["AS"]) + ":" + str(10)
                                conf_files[router["index"]].write("vrf definition client_" + str(neighbor["AS"]) + "\n")
                                conf_files[router["index"]].write(" rd " + str(neighbor["AS"]) + ":" + str(router["index"] + 1) + "\n")
                                conf_files[router["index"]].write(" route-target export " + neighbor["vrf"] + "\n")
                                conf_files[router["index"]].write(" route-target import " + neighbor["vrf"] + "\n")
                                conf_files[router["index"]].write(" !\n")
                                conf_files[router["index"]].write(" address-family ipv4\n")
                                conf_files[router["index"]].write(" exit-address-family\n")
                                conf_files[router["index"]].write("!\n")
                            # Connection of VRF to the interface
                            conf_files[router["index"]].write("interface " + neighbor["interface"] + '\n')
                            conf_files[router["index"]].write(" vrf forwarding client_" + str(neighbor["AS"]) + "\n")
                            conf_files[router["index"]].write(" ip address " + neighbor["ip"] + '\n')
                        else: # Peer
                            if not IPv4: # i.e. IPv6
                                conf_files[router["index"]].write(" no ip address\n")
                                conf_files[router["index"]].write(" ipv6 address " + neighbor["ip"] + '\n')
                                conf_files[router["index"]].write(" ipv6 enable\n")
                                if (IGP == "ospf"):
                                    conf_files[router["index"]].write(" ipv6 " + AS["IGP"] + ' ' + str(router["index"] + 1) + "00 " + "area 0\n")
                                elif (IGP == "ripng"):
                                    if not router["border-router"] or links[router["index"]][neighbor_router["index"]] != 2:
                                        conf_files[router["index"]].write(" ipv6 rip RIPng enable\n")
                    conf_files[router["index"]].write("!\n")
                    

def write_bgp_conf(conf_files, ip_matrix, intents):
    """
    Writes BGP configuration.

            Parameters:
                    conf_files (array of file objects): Array of configuration files
                    ip_matrix (2D matrix of strings): M[i][j] is the IP address of router i connected to router j
                    intents (dictionary): contains configuration requirements for the network
    """
    for AS in intents["AS"]:
        IPv4 = (AS["IP-version"] == 4)
        iBGP = AS["BGP"]["iBGP"]

       
        for router in AS["routers"]:

            # iBGP configuration
            address_families = {}
            if (iBGP == "full-meshed"):
                address_families["ipv6"] = []
                for same_AS_router in AS["routers"]:
                    if(router != same_AS_router):
                        ip = same_AS_router["loopback"][:-4]
                        conf_files[router["index"]].write(f" neighbor {ip} remote-as " + str(AS["number"]) + '\n')
                        conf_files[router["index"]].write(f" neighbor {ip} update-source loopback 0\n")
                        address_families["ipv6"].append(f"  neighbor {ip} activate\n")
                # Writes announced networks of each border-router, i.e. all networks in the AS
                if not IPv4:
                    if (router["border-router"]):    
                        for network in AS["IP-range"]["networks"]:
                            address_families["ipv6"].append(f"  network {network}\n")
                conf_files[router["index"]].write(" !\n")
            elif (iBGP == "PE full-meshed") and (router["border-router"]):
                address_families["vpnv4"] = []
                conf_files[router["index"]].write("router bgp " + str(AS["number"]) + "\n")
                for same_AS_router in AS["routers"]:
                    if(router != same_AS_router) and (same_AS_router["border-router"]):
                        ip, _ = same_AS_router["loopback"].split('/')
                        conf_files[router["index"]].write(f" neighbor {ip} remote-as " + str(AS["number"]) + '\n')
                        conf_files[router["index"]].write(f" neighbor {ip} update-source loopback 0\n")
                        address_families["vpnv4"].append(f"  neighbor {ip} activate\n")
                conf_files[router["index"]].write(" !\n")
            elif (iBGP == "PE route reflector"):
                if ("route-reflector" in router):
                    address_families["vpnv4"] = []
                    conf_files[router["index"]].write("router bgp " + str(AS["number"]) + "\n")
                    for same_AS_router in AS["routers"]:
                        if(router != same_AS_router) and (same_AS_router["border-router"]):
                            ip, _ = same_AS_router["loopback"].split('/')
                            conf_files[router["index"]].write(f" neighbor {ip} remote-as " + str(AS["number"]) + '\n')
                            conf_files[router["index"]].write(f" neighbor {ip} update-source loopback 0\n")
                            address_families["vpnv4"].append(f"  neighbor {ip} activate\n")
                            address_families["vpnv4"].append(f"  neighbor {ip} route-reflector-client\n")
                    conf_files[router["index"]].write(" !\n")
                elif (router["border-router"]):
                    address_families["vpnv4"] = []
                    conf_files[router["index"]].write("router bgp " + str(AS["number"]) + "\n")
                    for same_AS_router in AS["routers"]:
                        if (router != same_AS_router) and ("route-reflector" in same_AS_router) :
                            ip, _ = same_AS_router["loopback"].split('/')
                            conf_files[router["index"]].write(f" neighbor {ip} remote-as " + str(AS["number"]) + '\n')
                            conf_files[router["index"]].write(f" neighbor {ip} update-source loopback 0\n")
                            address_families["vpnv4"].append(f"  neighbor {ip} activate\n")
                    conf_files[router["index"]].write(" !\n")

            # eBGP configuration: for peering link
            if router["border-router"]:
                for network in router["networks"]:
                    for neighbor in network:
                        remote_AS, neighbor_router = find_router(neighbor["name"], intents)
                        if (neighbor_router != None):
                            if neighbor_router["border-router"]:
                                ip = ip_matrix[neighbor_router["index"]][router["index"]][:-3] # IP address of the neighbor router on the peering link
                                conf_files[router["index"]].write(f" neighbor {ip} remote-as " + str(remote_AS) + '\n')
                                address_families["ipv6"].append(f"  neighbor {ip} activate\n")

            # Address families
            if ("ipv6" in address_families):
                conf_files[router["index"]].write(" address-family ipv6\n")
                for config_line in address_families["ipv6"]:
                    conf_files[router["index"]].write(config_line)
                conf_files[router["index"]].write(" exit-address-family\n")
                conf_files[router["index"]].write(" !\n")
            
            if ("vpnv4" in address_families):
                conf_files[router["index"]].write(" address-family vpnv4\n")
                for config_line in address_families["vpnv4"]:
                    conf_files[router["index"]].write(config_line)
                conf_files[router["index"]].write(" exit-address-family\n")
                conf_files[router["index"]].write(" !\n")

            if (IPv4):
                for network in router["networks"]:
                        for neighbor in network:
                            if ("AS" in neighbor):
                                neighbor_ip, _ = neighbor["neighbor_ip"].split()
                                conf_files[router["index"]].write(" address-family ipv4 vrf client_" + str(neighbor["AS"]) + '\n')
                                conf_files[router["index"]].write(f"  neighbor {neighbor_ip} remote-as " + str(neighbor["AS"]) + '\n')
                                conf_files[router["index"]].write(f"  neighbor {neighbor_ip} activate\n")
                                conf_files[router["index"]].write(" exit-address-family\n")
                                conf_files[router["index"]].write(" !\n")

def write_igp_conf(conf_files, intents):
    """Writes specific IGP configuration lines for each router."""
    for AS in intents["AS"]:
        IGP = AS["IGP"].lower()
        IPv4 = (AS["IP-version"] == 4)
        for router in AS["routers"]:
            if IPv4:
                conf_files[router["index"]].write(f"router ospf {OSPF_PROCESS_ID}\n")
                conf_files[router["index"]].write("!\n")
            else: # IPv6
                if IGP == "ospf":
                    conf_files[router["index"]].write("ipv6 router ospf " + str(router["index"]  + 1) + "00\n") 
                    conf_files[router["index"]].write(" router-id " + (str(router["index"] + 1) + '.')*3 + str(router["index"] + 1) + '\n')
                elif IGP == "ripng":
                    conf_files[router["index"]].write("ipv6 router rip RIPng\n") 
                    conf_files[router["index"]].write(" redistribute connected\n")
                conf_files[router["index"]].write("!\n")

                if router["border-router"]:
                        for network in router["networks"]:
                            for neighbor in network:
                                _, neighbor_router = find_router(neighbor["name"], intents)
                                if neighbor_router["border-router"]:
                                    conf_files[router["index"]].write("router ospf " + str(router["index"] + 1) + "00\n")
                                    conf_files[router["index"]].write(" passive-interface "+ neighbor["interface"] + "\n")
                                    conf_files[router["index"]].write("!\n")
            




