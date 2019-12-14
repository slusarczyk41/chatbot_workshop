import random
import requests
from flask import Flask, request
import bs4
import pandas as pd


app = Flask(__name__)
ACCESS_TOKEN = 'EAAMEwNykko0BALgIQ3SgdVn75nOFPMpZC8mz6jgWCuCUhrdbbnXZAhtiXeiApZAgpyTMtv2UQVnZCRGojXd7mPBPdpm8WuhPllv8IMGtkEcPvTMaR8s389nfUfh4fFUFLoiXxVPnSBg1w3fDnU1ZAKZC2cfIfGxtzBW0TaQmROZAtajTGs2f5wb'
VERIFY_TOKEN = '12345'


sites_config = {
    'onet': {
        'www': "https://onet.pl",
        'search_pattern': ['a', 'itemBox'],
    }
}
global search_term


def respond(recipient_id, payload):
    body = {
        'messaging_type': 'RESPONSE',
        'recipient': {
            'id': recipient_id
        },
        'message': payload
    }

    response = requests.post(
        'https://graph.facebook.com/v5.0/me/messages?access_token='+ACCESS_TOKEN,
        json=body
    )

    return response.json()


def verify_fb_token(token_sent):
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'


@app.route("/", methods=['GET'])
def verify_message():
    token_sent = request.args.get("hub.verify_token")
    return verify_fb_token(token_sent)


def respond_hi():
    return {
        'text': 'Cześć, o czym chciałbyś dzisiaj poczytać? Wpisz "szukaj" + frazę '+
        'która Cię interesuje, np.: \n\nszukaj Andrzej Duda\n\n'+
        'A wyszukam dla Ciebie najbardziej aktualne artykuły z głównych stron gazet na ten temat'
    }


def respond_avaidable_sites(term):
    return {"attachment": {
        "type": "template",
        "payload": {
          "template_type":"generic",
          "elements":[
             {
              "title":x[0],
              "image_url":x[1],
              "buttons":[{
                "type":"postback",
                "title":x[0],
                "payload":x[2]
              }]
             } for x in [
                  [
                      'Gazeta Wyborcza',
                      'http://wschodyfestiwal.pl/wp-content/uploads/2018/03/gazeta-wyborcza-patron-medialny-festiwalu-wschody-logo-2018.jpg',
                      'wyborcza'
                  ],
                  [
                      'Gazeta.pl',
                      'http://www.razemlepiej.pl/wp-content/uploads/2015/02/Gazeta_pl.png',
                      'gazeta'
                  ],
                  [
                      'Onet',
                      'https://pbs.twimg.com/profile_images/1087710090499637248/cclW5bFA_400x400.jpg',
                      'onet'
                  ],
                  [
                      'Wszędzie',
                      'https://media.istockphoto.com/vectors/newspaper-drawing-vector-id166054637?k=6&m=166054637&s=612x612&w=0&h=UR7jdgQ1zkYE9K8EgVmQgUZeHcIwRjqeCjDdSRHo-9A=',
                      'all'
                  ]
              ]
          ]
        }
    }}


def get_article_list(brand):
    if brand == 'onet':
        soup = bs4.BeautifulSoup(requests.get("https://onet.pl").text, features = "html.parser")
        found_articles = soup.find_all('a', 'itemBox')
        return [(x.find_all('span')[3].text.strip(), x['href'], "https:"+x.find_all('img')[0]['src']) for x in found_articles]
    elif brand == 'gazeta':
        soup = bs4.BeautifulSoup(requests.get("https://gazeta.pl").text, features = "html.parser")
        found_articles = []
        found_articles = []
        for x in soup.find_all('a'):
            try:
                if 'Nav' not in x['href']:
                    if 'StLinks' not in x['href']:
                        try:
                            src = x.find_all('img')[0]['data-src']
                        except:
                            try:
                                src = x.div.div.div['style'].replace('background-image: url(', '').replace(');', '')
                            except:
                                try:
                                    src = x.div.div.div['data-src-style'].replace('background-image: url(', '').replace(');', '')
                                except:
                                    src = 'https://media.istockphoto.com/vectors/newspaper-drawing-vector-id166054637?k=6&m=166054637&s=612x612&w=0&h=UR7jdgQ1zkYE9K8EgVmQgUZeHcIwRjqeCjDdSRHo-9A='
                        found_articles.append((x['title'], x['href'], src))
            except:
                pass
        return found_articles
    elif brand == 'wyborcza':
        soup = bs4.BeautifulSoup(requests.get("https://wyborcza.pl/0,0.html?disableRedirects=true").text)
        found_articles = []
        for x in soup.find_all('a'):
            try:
                if x['title'] != None and x['href'] != None:
                    found_articles.append((x['title'], x['href'], 'https://media.istockphoto.com/vectors/newspaper-drawing-vector-id166054637?k=6&m=166054637&s=612x612&w=0&h=UR7jdgQ1zkYE9K8EgVmQgUZeHcIwRjqeCjDdSRHo-9A='))
            except:
                pass
        return found_articles


def respond_article_list(term, brand):
    if brand != 'all':
        articles = get_article_list(brand)
    else:
        articles_container = []
        for brand in ['onet', 'gazeta', 'wyborcza']:
            articles_container.append(get_article_list(brand))
        articles = [i for j in articles_container for i in j]

    articles_with_search_term = [x for x in articles if term.lower() in x[0].lower()]
    distinct = pd.DataFrame(articles_with_search_term).drop_duplicates(subset = [0]).values.tolist()

    return {"attachment": {
        "type": "template",
        "payload": {
          "template_type":"generic",
          "elements":[
             {
              "title":x[0],
              "image_url":x[2],
              "default_action": {
                "type": "web_url",
                "url": x[1],
                "webview_height_ratio": "tall",
              }
             } for x in distinct
          ]
        }
    }}


@app.route("/", methods=['POST'])
def handle_webhook():
    output = request.get_json()
    data = output['entry'][0]['messaging'][0]
    sender_id = data['sender']['id']

    print('----')
    print(data)
    print('----')

    # Chosen brand
    if 'postback' in data.keys():
        global search_term
        found_articles = respond_article_list(search_term, data['postback']['payload'])
        if len(found_articles['attachment']['payload']['elements']) != 0:
            print('przed wyswietleniem')
            respond(sender_id, found_articles)
            print(found_articles)
            print('po')
        else:
            respond(sender_id, {"text": "Nie udało mi się nic znaleźć :("})
        return 'ok'

    message = data['message']

    # Search term
    if 'szukaj' in message['text'].lower():
        search_term = message['text'].lower().replace('szukaj','').strip()
        if search_term != '':
            print('przed wyswietleniem')
            respond(sender_id, respond_avaidable_sites(search_term))
            print('po')
        else:
            respond(sender_id, {"text": "Wpisz jakąś frazę!"})

    # Initial message
    elif message['text']:
        respond(sender_id, respond_hi())

    return 'ok'


if __name__ == "__main__":
    app.run(port = 5002, debug = True)
