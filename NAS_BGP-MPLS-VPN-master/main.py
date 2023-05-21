from shutil import copy
import json
import sys

from intents_util import count_routers, find_router_files, translate_intent
from ip_generator import createIPs
from config_generator import *


def deplace_config_files(conf_files, router_dir):
    """Copies and pastes router configuration files from the working directory to the GNS3 directory."""
    print("NOTE: The following configuration files have been moved to their directories")
    for i in range(len(conf_files)):
        copy(src=conf_files[i].name, dst=router_dir[i])
        print(f"{conf_files[i].name} => {router_dir[i]}")
    


def get_instructions(user_input):
    if (len(user_input) == 1):
        return user_input[0], None
    elif (len(user_input) > 1):
        return user_input[0], user_input[1]


if __name__ == "__main__":
    # Get user intructions
    if (len(sys.argv[1:]) == 0):
        sys.exit("ERROR: No instruction, need at least intent file.")
    else:
        intent_file = ""
        user_intent, project = get_instructions(sys.argv[1:])
        try:
            intent_path = translate_intent(
                user_intent, project, INTENTS_DIR, JSON_DIR)
        except Exception as err:
            intent_file = user_intent
            intent_path = f"{INTENTS_DIR}/{intent_file}"

    # Loads JSON intent file
    with open(intent_path, "r") as intent_file:
        intents = json.load(intent_file)

    # Initializes configuration files
    NB_ROUTERS = count_routers(intents)
    conf_files = init_config_file(NB_ROUTERS, intents)

    # Writes configuration of interfaces for each router
    links, ip_matrix = createIPs(intents, NB_ROUTERS)
    write_interface_conf(conf_files, ip_matrix, links, intents)

    # Writes BGP configuration
    write_bgp_conf(conf_files, ip_matrix, intents)

    # Writes lines to activate IGP
    write_igp_conf(conf_files, intents)

    # Writes end of default configuration
    finish_config_file(conf_files)

    # Deplaces configuration files in GNS3 repositories
    routers_files = find_router_files(intents["AS"], conf_files)
    deplace_config_files(conf_files, routers_files)

    # Creates a JSON file containing generated configurations
    with open(FINAL_INTENTS_FILE, "w") as final_intents:
        json.dump(intents, final_intents, indent=4)
