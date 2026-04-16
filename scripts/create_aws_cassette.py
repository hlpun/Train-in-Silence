import yaml
import json

# Minimal products and terms for us-east-1 g4dn.xlarge
sku = "3RT6W3PX4VZ6G6Z3"
data = {
    "formatVersion": "v1.0",
    "offerCode": "AmazonEC2",
    "products": {
        sku: {
            "sku": sku,
            "productFamily": "Compute Instance",
            "attributes": {
                "instanceType": "g4dn.xlarge",
                "location": "US East (N. Virginia)",
                "operatingSystem": "Linux",
                "preInstalledSw": "NA",
                "tenancy": "Shared",
                "capacitystatus": "Used",
                "marketoption": "OnDemand"
            }
        }
    },
    "terms": {
        "OnDemand": {
            sku: {
                sku + ".JRTCKXETXF": {
                    "priceDimensions": {
                        sku + ".JRTCKXETXF.6YS6EN2CT7": {
                            "unit": "Hrs",
                            "pricePerUnit": {"USD": "0.526"}
                        }
                    }
                }
            }
        }
    }
}

cassette = {
    "interactions": [
        {
            "request": {
                "body": "",
                "headers": {},
                "method": "GET",
                "uri": "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/current/us-east-1/index.json"
            },
            "response": {
                "body": {
                    "string": json.dumps(data)
                },
                "headers": {"Content-Type": ["application/json"]},
                "status": {"code": 200, "message": "OK"}
            }
        }
    ],
    "version": 1
}

with open("tests/cassettes/test_networking/test_aws_public_price_list_fetch.yaml", "w") as f:
    yaml.dump(cassette, f)

print("Created minimal AWS cassette.")
