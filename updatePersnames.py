import requests, csv, json, time
from urllib.parse import quote
from asnake.client import ASnakeClient

viafURL = 'http://viaf.org/viaf/search?query=local.personalNames+%3D+%22'

# # print instructions
print('This script queries existing person agent records in ArchivesSpace with the source of "viaf" and updates them with the proper/updated name form from VIAF (if one exists) and appends the VIAF URI to the existing records.  Please note: This is a PROOF OF CONCEPT script, and should not be used in production settings without thinking this through!')
input('Press Enter to continue...')

# This is where we connect to ArchivesSpace.  See authenticate.py
client = ASnakeClient()
client.authorize() # login, using default values

# search AS for person agents with source "viaf"
query = json.dumps({"query":{
    "jsonmodel_type":"boolean_query",
    "op":"AND",
    "subqueries":[
        {
            "jsonmodel_type":"field_query",
            "field":"primary_type",
            "value":"agent_person",
            "literal":True
        },
        {
            "jsonmodel_type":"field_query",
            "field":"source",
            "value":"viaf",
            "literal":True
        }
    ]
}})
ASoutput = list(client.get_paged("/search", params={"filter": query}))
print('Found ' + str(len(ASoutput)) + ' agents.')

# grab uri out of agent
for person in ASoutput:
    uri = person['uri']
    personRecord = client.get(uri).json()
    lockVersion = str(personRecord['lock_version'])
    primary_name = personRecord['names'][0]['primary_name']
    try:
        secondary_name = personRecord['names'][0]['rest_of_name']
    except:
        secondary_name = ''
    try:
        dates = personRecord['names'][0]['dates']
    except:
        dates = ''
    searchName = primary_name + ', ' + secondary_name + ', ' + dates
    nameEdited = quote(searchName.strip())
    url = viafURL+nameEdited+'%22+and+local.sources+%3D+%22lc%22&sortKeys=holdingscount&maximumRecords=1&httpAccept=application/rdf+json'
	# first need to treat the response as text since we get an xml resopnse (with json embedded inside)
    response = requests.get(url).text
    try:
        response = response[response.index('<recordData xsi:type="ns1:stringOrXmlFragment">')+47:response.index('</recordData>')].replace('&quot;','"')
        response = json.loads(response)
        properName = response['mainHeadings']['data'][0]['text']
        nameArray = properName.split(',')
        properPrimary = nameArray[0]
        try:
            properSecondary = nameArray[1]
        except:
            properSecondary = ''
        try:
            properDates = nameArray[2]
        except:
            properDates = ''
        viafid = response['viafID']
    except:
        label = ''
        viafid = ''
    if viafid != '':
        links = json.loads(requests.get('http://viaf.org/viaf/'+viafid+'/justlinks.json').text)
        viafid = 'http://viaf.org/viaf/'+viafid
    toPost = {"lock_version": lockVersion,
              "names": [
                  {"primary_name": properPrimary.strip(),
                   "rest_of_name": properSecondary.strip(),
                   "dates": properDates.strip(),
                   "sort_name":properName,
                   "authorized":True,
                   "is_display_name": True,
                   "source": "viaf",
                   "rules": "dacs",
                   "name_order": "inverted",
                   "jsonmodel_type": "name_person",
                   "authority_id": viafid
                  }
              ]
    }
    post = client.post(uri, json=toPost).json()
    print(post)
