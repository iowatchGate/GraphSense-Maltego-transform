from maltego_trx.maltego import MaltegoEntity, MaltegoTransform, Phrase
from maltego_trx.overlays import OverlayPosition, OverlayType

from graphsense.configuration import Configuration

import json

import re as regex

from graphsense.api import addresses_api, entities_api
from graphsense.api_client import ApiClient, ApiException

from datetime import datetime

def open_config():
	error= ""
	try:
		with open("config.json") as json_data_file:
			config = json.load(json_data_file)
		if "token" not in config or "api" not in config:
			print("Error message: Cannot load data from config.json file")
		else:
			configuration = Configuration(
			host = config["api"],
			api_key = {'api_key': config["token"]}
			)
	except Exception as e:
		error = "Could not read config.json. Error: " + str(e)
	return configuration, error
	
def get_currency(virtual_asset_address):
	#supported_currencies are "btc"(not!), "bch", "ltc", "zec", "eth" (note: a BTC address could also be a bch address)
	currency = []
	virtual_asset_match = regex.search(r"\b([13][a-km-zA-HJ-NP-Z1-9]{25,34})|bc(0([ac-hj-np-z02-9]{39}|[ac-hj-np-z02-9]{59})|1[ac-hj-np-z02-9]{8,87})\b", virtual_asset_address)
	if virtual_asset_match:
		currency = ["btc"]
	virtual_asset_match = regex.search(r"\b((?:bitcoincash|bchtest):)?([0-9a-zA-Z]{34})\b", virtual_asset_address)
	if virtual_asset_match:
		currency += ["bch"]
	virtual_asset_match = regex.search(r"\b[LM3][a-km-zA-HJ-NP-Z1-9]{25,33}\b", virtual_asset_address)
	if virtual_asset_match:
		currency = ["ltc"]
	virtual_asset_match = regex.search(r"\b[tz][13][a-km-zA-HJ-NP-Z1-9]{33}\b", virtual_asset_address)
	if virtual_asset_match:
		currency = ["zec"]
	virtual_asset_match = regex.search(r"\b(0x)?[0-9a-fA-F]{40}\b", virtual_asset_address)
	if virtual_asset_match:
		currency = ["eth"]
	return currency

def get_currency_from_entity_details(entity_details):
	currency = []
	if ('maltego.BTCAddress' in entity_details):
		currency = ["btc"]
	if ('maltego.BCHAddress' in entity_details):
		currency = ["bch"]
	if ('maltego.LTCAddress' in entity_details):
		currency = ["ltc"]
	if ('maltego.ZECAddress' in entity_details):
		currency = ["zec"]
	if ('maltego.ETHAddress' in entity_details):
		currency = ["eth"]
	return currency

def get_address_details(currency, address):
	error= ""
	configuration = open_config()[0]

	with ApiClient(configuration) as api_client:
		api_instance = addresses_api.AddressesApi(api_client)
		try:
			# Retrieve the address object
			address_obj = api_instance.get_address(currency, str(address), include_tags = True)
		except ApiException as e:
			error = ("Exception when calling AddressesApi: " + str (e))
			address_obj = [""]
		return address_obj, error

def get_entity_details(currency, entity):
	error= ""
	configuration = open_config()[0]

	with ApiClient(configuration) as api_client:
		api_instance = entities_api.EntitiesApi(api_client)
		try:
			entity_obj = api_instance.get_entity(currency, entity, include_tags = True)
		except ApiException as e:
			error = ("Exception when calling EntitiesApi: " + str(e))
			entity_obj = []
		return entity_obj, error

def create_entity_with_details(json_result,currency,query_type,response): # Query_type is one of : "known_entities", "tags", "details", "cluster"
	error= ""
	
	if currency == "btc":
		set_type = "maltego.BTCAddress"
	if currency == "bch":
		set_type = "maltego.BCHAddress"
	if currency == "ltc":
		set_type = "maltego.LTCAddress"
	if currency == "zec":
		#set_type = "maltego.CryptocurrencyAddress"
		set_type = "maltego.ZECAddress"
	if currency == "eth":
		set_type = "maltego.ETHAddress"


	if query_type == "details":
		#if currency == "cluster":
		if not ('address' in json_result): # This means this is a cluster not a cryptocurrency address
			#currency = json_result['tags']['address_tags'][0]['currency']
			set_type = "maltego.CryptocurrencyWallet"
			cluster_ID = json_result['entity'] #the Cluster ID is known as "entity" in GraphSense API json result
			entity = response.addEntity(set_type, cluster_ID)
		
			json_result = get_entity_details(currency,json_result['entity'])
			if ('1' in json_result):
				error = "Got an error checking the cluster details: " + json_result[1]
				return "", error
			else:
				json_result = json_result[0]
		
			entity.addProperty("num_addresses", "Number of addresses", value=json_result['no_addresses'])
		else:
			if 'properties.cryptocurrencyaddress' in json_result:
				address = json_result['properties.cryptocurrencyaddress']
			else:
				address = json_result['address']
			entity = response.addEntity(set_type, address)
			#entity.addProperty("properties.cryptocurrencyaddress", value=json_result['address'])
			entity.addProperty(set_type, value=json_result['address'])
			
		#entity.setType(set_type)
		#entity.addOverlay('#ffffff', OverlayPosition.NORTH_WEST, OverlayType.IMAGE)#First we reset the overlay, just to be clean
		#if (json_result['tags']!=[]):
		if ('tags' in json_result) or ('address_tags' in json_result) or ('entity_tags' in json_result):
			entity.addOverlay('Businessman', OverlayPosition.NORTH_WEST, OverlayType.IMAGE)
		else:
			entity.addOverlay('', OverlayPosition.NORTH_WEST, OverlayType.IMAGE) # reset the overlay
			# if (json_result['tags']['address_tags']!=[]):
# 				entity.addOverlay('#45e06f', OverlayPosition.NORTH_WEST, OverlayType.COLOUR)
# 			else:
# 				if (json_result['tags']['entity_tags']!=[]):
# 					entity.addOverlay('#45e06f', OverlayPosition.NORTH_WEST, OverlayType.COLOUR)
# 				else:
# 					if (json_result['tags']['entity_tags']!=[]):
# 						entity.addOverlay('#45e06f', OverlayPosition.NORTH_WEST, OverlayType.COLOUR)

			
		balance_value = json_result['balance']['value']#/100000000 # Satoshis to BTCs 10e-9
		total_received_value = json_result['total_received']['value']#/100000000 # Satoshis to BTCs 10e-9
		total_sent_value = json_result['total_spent']['value']#/100000000 # Satoshis to BTCs 10e-9
		balance_fiat_value = json_result['balance']['fiat_values'][0]['value']
		balance_fiat_currency = json_result['balance']['fiat_values'][0]['code']
		num_transactions = json_result['no_incoming_txs']+json_result['no_outgoing_txs']
		cluster_ID = json_result['entity']
		total_throughput = total_received_value + total_sent_value
		last_tx_datetime = datetime.fromtimestamp(json_result['last_tx']['timestamp'])
		first_tx_datetime = datetime.fromtimestamp(json_result['first_tx']['timestamp'])
		
		entity.addProperty("currency", "Currency", value=currency)
		entity.addProperty("final_balance", "Final balance (" + currency + ")", value=balance_value)
		entity.addProperty("final_balance_fiat", "Final balance (" + balance_fiat_currency + ")", value=balance_fiat_value)
		entity.addProperty("total_throughput", "Total throughput", value=total_throughput)
		entity.addProperty("total_received", "Total received", value=total_received_value)
		entity.addProperty("total_sent", "Total sent", value=total_sent_value)
		entity.addProperty("num_transactions","Number of transactions", value=num_transactions)
		entity.addProperty("num_in_transactions","Number of incoming transactions", value=json_result['no_incoming_txs'])
		entity.addProperty("num_out_transactions","Number of outgoing transactions", value=json_result['no_outgoing_txs'])
		entity.addProperty("cluster_ID", "Cluster ID", "loose", value=cluster_ID)
		entity.addProperty("Last_tx", "Last transaction (UTC)", value=last_tx_datetime)
		entity.addProperty("First_tx", "First transaction (UTC)", value=first_tx_datetime)

	if query_type == "cluster":
		set_type = "maltego.CryptocurrencyWallet"
		cluster_ID = json_result['entity'] #the Cluster ID is known as "entity" in GraphSense API json result
		entity = response.addEntity(set_type, cluster_ID)
		
		json_result = get_entity_details(currency, cluster_ID)
		if ('1' in json_result):
			error = "Got an error getting the cluster ID: " + json_result[1]
			return "", error
		else:
			json_result = json_result[0]
		
		entity.addProperty("cryptocurrency.wallet.name", value=cluster_ID)
		entity.addProperty("cluster_ID", "Cluster ID", value=cluster_ID)
		entity.addProperty("currency","Currency", "strict", value=currency)
		if ('tags' in json_result) or ('address_tags' in json_result) or ('entity_tags' in json_result):
			entity.addOverlay('Businessman', OverlayPosition.NORTH_WEST, OverlayType.IMAGE)
		else:
			entity.addOverlay('', OverlayPosition.NORTH_WEST, OverlayType.IMAGE) # reset the overlay
			
	if query_type == "tags":
		tags = []
		set_type = "maltego.CryptocurrencyOwner"
		
		json_result = get_address_details(currency, json_result['address']) # We query the entity to get the "Address" and the "Entity" (cluster) tags if any.
		if ('1' in json_result):
			error = "Got an error getting the address tags: " + json_result[1]
			return "", error
		else:
			json_result = json_result[0]
		
		if ('tags' in json_result):
			tags = json_result['tags']
			if ('address_tags' in tags):
				tags = tags['address_tags']
			if tags:
				if "error" in tags:
					error = str("error in address tags: " + graphsense_tag["error"]["message"])
				# Create new entity for each tag we found
				# If we have the same tag multiple times, Maltego will merge them automatically
				for tag in tags:
					if "label" in tag:
						entity=response.addEntity("Cryptocurrency", tag["label"])
						entity.setLinkLabel("To tags [GraphSense] (" + tag["currency"] + ")")
						entity.setType("maltego.CryptocurrencyOwner")
					if "category" in tag:
						entity.addProperty("OwnerType", "loose", tag["category"])
					if "source" in tag:
						entity.addProperty("Source_URI", "Source", "loose", value=tag["source"])
						uri_link = str('<a href="' + str(tag["source"]) + '">' + str(tag["source"]) + '</a>')
						entity.addDisplayInformation(uri_link,"Source URI")
					if "abuse" in tag:
						entity.addProperty("Abuse_type", "Abuse type", "loose", value=tag["abuse"])
			else:
				entity = ""
				error = "No attribution tags found for this address in " + currency 

	if query_type == "entity_tags": #(that's the tags at cluster level)
		tags = []
		set_type = "maltego.CryptocurrencyOwner"
		
		json_result = get_entity_details(currency, json_result['entity']) #address here is actually the Entity Wallet which is the GraphSense Cluster ID
		if ('1' in json_result):
			error = "Got an error getting the tags in this cluster: " + json_result[1]
			return "", error
		else:
			json_result = json_result[0]
		
		if ('tags' in json_result):
			tags = json_result['tags']
			if ('entity_tags' in tags):
				tags = tags['entity_tags']
				if tags:
					if "error" in tags:
						error = str("error in cluser tags: " + graphsense_tag["error"]["message"])
					# Create new entity for each tag we found
					# If we have the same tag multiple times, Maltego will merge them automatically
					for tag in tags:
						if "label" in tag:
							entity=response.addEntity("Cryptocurrency", tag["label"])
							entity.setLinkLabel("To tags [GraphSense] (" + tag["currency"] + ")")
							entity.setType("maltego.CryptocurrencyOwner")
						if "category" in tag:
							entity.addProperty("OwnerType", "Owner type", "loose", tag["category"])
						if "address" in tag:
							entity.addProperty("Address", "Address", "", tag["address"])
						if "source" in tag:
							entity.addProperty("Source_URI", "Source", "loose", value=tag["source"])
							uri_link = str('<a href="' + str(tag["source"]) + '">' + str(tag["source"]) + '</a>')
							entity.addDisplayInformation(uri_link,"Source URI")
						if "abuse" in tag:
							entity.addProperty("Abuse_type", "Abuse type", "loose", value=tag["abuse"])
			tags = json_result['tags']
			if ('address_tags' in tags):
				tags = tags['address_tags']
				if tags:
					if "error" in tags:
						error = str("error in cluster address tags: " + graphsense_tag["error"]["message"])
					# Create new entity for each tag we found
					# If we have the same tag multiple times, Maltego will merge them automatically
					for tag in tags:
						if "label" in tag:
							entity=response.addEntity("Cryptocurrency", tag["label"])
							entity.setLinkLabel("To tags [GraphSense] (" + tag["currency"] + ")")
							entity.setType("maltego.CryptocurrencyOwner")
						if "category" in tag:
							entity.addProperty("OwnerType", "Owner type", "loose", tag["category"])
						if "address" in tag:
							entity.addProperty("Address", "Address", "", tag["address"])
						if "source" in tag:
							uri_link = str('<a href="' + str(tag["source"]) + '">' + str(tag["source"]) + '</a>')
							entity.addProperty("Source_URI", "Source URI", "loose", str(tag["source"]))
							entity.addDisplayInformation(uri_link,"Source URI")
						if "abuse" in tag:
							entity.addProperty("Abuse_type", "Abuse type", "loose", value=tag["abuse"])
		else:
			error = "No attribution tags found for this cluster"

	return entity, error
