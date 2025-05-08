#!/usr/bin/python3
import requests # type: ignore
import argparse
import os
import configparser
import urllib3 # type: ignore
import pprint
import secrets
import string
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

## Initialize variables
kc_url = ""
client_secret = ""

## Parse arguments
parser = argparse.ArgumentParser(
    prog="kc-api-get.py",     
    description="A sample CLI tool for retrieving realm list, clients, users, client-scopes groups and roles in JSON format from a Keycloak REST API.",
    epilog="Red Hat Customer Success Architects sample code")

parser.add_argument(
    "config", 
    nargs='?',  
    help="Configures the access to the Keycloak API for the client admin-cli")

parser.add_argument(
    "--realm", 
    help="Select the realm",
    required=False)

list_of_resources = ["clients", "client-scopes", "users", "groups", "roles"]
parser.add_argument(
    "--resource", 
    help="Query resource information from realm selected",
    required=False, 
    choices=list_of_resources)

parser.add_argument(
    "--action", 
    help="Selected an action for an resource", 
    required=False,
    choices=["create", "delete"]
)
args = parser.parse_args()

if (args.realm and args.resource is None):
    parser.error("--realm option requires --resource.")

if (args.realm is None and args.resource):
    parser.error("--resource requires to set a realm with --realm.")

# Configure the CLI
CONFIG_FILE = "./.config"
config_obj = configparser.ConfigParser()

if os.path.isfile(CONFIG_FILE): 
   with open(CONFIG_FILE, "r") as file_object:
    config_obj.read_file(file_object)
    kc_url=config_obj.get("API", "url")
    client_secret=config_obj.get("API", "client_secret")
else: 
    if args.config is None: 
        print("Run 'kc-api-get.py config' first to configure Keycloak REST API Access.")
        exit(1)

if args.config:
    print("Configure KC API Get samples CLI for the admin-cli client")
    kc_url_input = input("- Keycloak URL[" + kc_url + "]: ")
    if kc_url_input != "": 
        kc_url = kc_url_input
    client_secret_input = input("- Client Secret[" + client_secret + "]: ")
    if client_secret_input != "":
        client_secret = client_secret_input
    config_obj["API"] = {"url": kc_url, "client_secret": client_secret}
    with open(CONFIG_FILE, "w") as file_obj:
        config_obj.write(file_obj)
    exit(0)

# Retrieve Bearer token from requests
headers={"Content-Type":"application/x-www-form-urlencoded"}
data = {
    "grant_type": "client_credentials",
    "client_id": "admin-cli",
    "client_secret": client_secret }

token_url="{}/realms/master/protocol/openid-connect/token".format(kc_url)
response = requests.post(
    url=token_url,
    headers=headers, 
    data=data, 
    verify=False)

# Set the Authorization header to the Bearer token retrieved
responseJson = response.json()
access_token=response.json()['access_token']
headers={
    "Content-Type":"application/json", 
    "Authorization": "Bearer {}".format(access_token)}

if args.resource is None:
    query_url = "{}/admin/realms/?briefRepresentation=true".format(kc_url)
else:
    query_url =  "{base_url}/admin/realms/{realm}/{resource}".format(
        base_url=kc_url, 
        realm=args.realm, 
        resource=args.resource)

# Perform the API call
response = requests.get(
    url=query_url, 
    headers = headers, 
    verify=False)

if response.ok: 
    #pprint.pprint(response.text, compact=False)
    users = response.json()
    print(json.dumps(response.json(), indent=2)) 
else:
    print("Error performing API call:  " + query_url)
    print("- error code: " + response.status_code)
    print("- headers: ")
    pprint.pprint(headers, compact=True)
    print("---")

if args.action is None:
    exit(0)
else:
    if args.action == "create":
        # Create users
        print("Creating users...")
        alphabet = string.ascii_letters + string.digits
        for index in range(10):
            user = f"user{index+1}"
            print(f"- Username: {user}")
            password = ''.join(secrets.choice(alphabet) for i in range(12))  # for a 12-character password
            print(f"  Paossword: {password}")
            user_payload = {
                "username": user,
                "credentials": [{
                    "type": "password", 
                    "value": password, 
                    "temporary": False    
                }],
                "enabled": True
            }
            response = requests.post(
                query_url, 
                headers = headers,
                json = user_payload,
                verify=False)
            response.raise_for_status()
            location = response.headers["Location"]
            print(location)
            #pprint.pprint(user_payload)
    else:
        # Delete users
        for user in users:
            print(f"User id[User]: {user['id']}[{user['username']}]")
            url_delete_user = f"{kc_url}/admin/realms/{args.realm}/users/{user['id']}"
            responseDelete = requests.delete(
                url=url_delete_user,
                headers=headers, 
                verify=False
            )
            responseDelete.raise_for_status()
            print(f" - User {user['username']} successfully deleted.")
        exit(0)