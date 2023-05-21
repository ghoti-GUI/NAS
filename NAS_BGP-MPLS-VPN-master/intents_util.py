import os


from json_transform import translate

OUTPUT_INTENT = "intents.json"


def translate_intent(intent_file, project, intents_dir, json_dir):
    if project == "NAS":
        output_path = f"{json_dir}/{OUTPUT_INTENT}"
        translate(f"{intents_dir}/{intent_file}", output_path)
        return output_path
    else:
        raise


def count_routers(intents):
    """Returns the number of routers in the intent file."""
    nb_routers = 0
    for AS in intents["AS"]:
        for router in AS["routers"]:
            router["index"] = nb_routers
            nb_routers += 1
    return nb_routers


def find_router(name, intents):
    """Searches a router and its AS number and returns both."""
    for AS in intents["AS"]:
        for router in AS["routers"]:
            if (router["name"] == name):
                return AS["number"], router
    return None, None


def get_netmask(slashed_mask):
    """Returns the complete netmask according to the given slashed mask."""
    return "255.255.255.0" if (slashed_mask == "/24") else "255.255.255.255"


def find_router_files(AS_list, conf_files):
    """Returns a list of all router files."""
    files = []
    for AS in AS_list:
        for router in AS["routers"]:
            files.append(router["GNS3_file"])

    for i in range(len(conf_files)):
        dirname, basename = os.path.split(conf_files[i].name)
        files[i] += f"/{basename}"

    return files
