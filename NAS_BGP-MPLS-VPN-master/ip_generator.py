from intents_util import find_router, get_netmask

def init_matrix(size):
    """Returns a zero-initialized squared matrix given its size."""
    matrix = []
    for _ in range(size):
        row = []
        for _ in range(size):    
            row.append(0)
        matrix.append(row)
    return matrix

def print_matrix(mat):
    """Prints a matrix in the terminal."""
    for row in mat:
        print(row)
    print("\n")


def createIPs(intents, nb_routers):
    """Returns and prints IP addresses of each routers and their adjacence matrix."""
    ip_matrix = init_matrix(nb_routers) # ip_matrix[i][j] is the IP address of router i connected to router j
    links = init_matrix(nb_routers) # marks links between routers : 0 not connected, 1 connected, 2 connected on peering link

    # Distributes IP subnetwork prefix for each link and updates 'links' matrix
    subnet_nb = 1
    for AS in intents["AS"]:
        for router in AS["routers"]:
            for network in router["networks"]:
                for neighbor_info in network:
                    _, neighbor = find_router(neighbor_info["name"], intents)
                    if (neighbor != None):
                        if not links[router["index"]][neighbor["index"]]:
                            ip_matrix[router["index"]][neighbor["index"]] = 1 if(router["border-router"] and neighbor["border-router"]) else subnet_nb
                            links[router["index"]][neighbor["index"]] = 2 if(router["border-router"] and neighbor["border-router"]) else 1
                            ip_matrix[neighbor["index"]][router["index"]] = ip_matrix[router["index"]][neighbor["index"]]
                            links[neighbor["index"]][router["index"]] = 1
                            subnet_nb += 1
        subnet_nb = 1
    print("**** ip matrix:")
    print_matrix(ip_matrix)
    print("**** links matrix:")
    print_matrix(links)

    # Creates IP adresses
    for AS in intents["AS"]:
        internal_network = AS["IP-range"]["physical"]["inAs"] # network prefix in the AS
        AS["IP-range"]["networks"] = [] # Adds a new entry in intents dictionary -> {"networks" : list of network prefixes in the AS}
        for router in AS["routers"]:
            for network in router["networks"]:
                for neighbor_info in network:
                    neighbor_AS, neighbor = find_router(neighbor_info["name"], intents)
                    if (neighbor != None):
                        if not isinstance(ip_matrix[router["index"]][neighbor["index"]], str): # i.e. there is no ip address
                            if (AS["number"] == neighbor_AS):
                                netmask = get_netmask(f"/{internal_network[-2:]}")
                                ip = ip_matrix[router["index"]][neighbor["index"]]
                                network = f"{internal_network[:-6]}{ip}."
                                AS["IP-range"]["networks"].append(f"{network} {netmask}")
                            network_suffix = 1 if (router["index"]<neighbor["index"]) else 2
                            ip_matrix[router["index"]][neighbor["index"]] = f"{network}{network_suffix} {netmask}"
    print("**** Final ip matrix:")
    print_matrix(ip_matrix)    

    return links, ip_matrix