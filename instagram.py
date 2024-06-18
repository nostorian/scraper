# insta scraper, made by nostorian, dc: @fw.nos

import tls_client
import re
import json
from bs4 import BeautifulSoup
import ua_generator


class InstagramScraper:
    def __init__(self, username):
        self.username = username
        self.session = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        self.base_url = f"https://www.instagram.com/{username}/"
        self.buisness_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}&hl=en"
        self.page_content = self.fetch_page_content()

    def fetch_page_content(self):
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                return response.text
            else:
                print(f"Failed to fetch page content: Status code {response.status_code}")
                return None
        except Exception as e:
            print(f"Failed to fetch page content: {e}")
            return None

    def parse_content(self, regex):
        if self.page_content:
            soup = BeautifulSoup(self.page_content, "html.parser").prettify()
            match = re.search(regex, soup)
            if match:
                return match.group(1)
        return None

    def fetch_all_tokens(self):
        tokens = {
            "csrf_token": self.get_csrf(),
            "device_id": self.get_device_id(),
            "app_id": self.get_app_id(),
            "user_id": self.get_user_id(),
            "haste_session": self.get_haste_session(),
            "revision": self.get_revision(),
            "lsd": self.get_lsd(),
            "jazoest": self.get_jazoest(),
            "cometreq": self.get_cometreq(),
            "spint": self.get_spint(),
            "hsi": self.get_hsi()
        }
        missing_tokens = [k for k, v in tokens.items() if v is None]
        if missing_tokens:
            print(f"Missing tokens: {', '.join(missing_tokens)}")
        return tokens

    def get_csrf(self):
        return self.parse_content(r'"csrf_token":"(.*?)"')

    def get_device_id(self):
        return self.parse_content(r'"device_id":"([A-Z0-9-]+)"')

    def get_app_id(self):
        return self.parse_content(r'"APP_ID":"(\d+)"')

    def get_user_id(self):
        return self.parse_content(r'"profilePage_([0-9]+)"')

    def get_haste_session(self):
        return self.parse_content(r'"haste_session":"(.*?)"')

    def get_revision(self):
        return self.parse_content(r'"__spin_r":(\d+)')

    def get_lsd(self):
        return self.parse_content(r'"lsd":"(.*?)"')

    def get_jazoest(self):
        return self.parse_content(r'jazoest=(\d+)')

    def get_cometreq(self):
        return self.parse_content(r'__comet_req=(\d+)')

    def get_spint(self):
        return self.parse_content(r'"__spin_t":(\d+)')

    def get_hsi(self):
        return self.parse_content(r'"hsi":"(.*?)"')

    def create_meta(self, tokens, asbd):
        user_agent = ua_generator.generate(device='desktop', browser='chrome')
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.8",
            "Connection": "keep-alive",
            "Host": "www.instagram.com",
            "Referer": self.base_url,
            "sec-ch-ua": user_agent.ch.brands,
            "sec-ch-ua-mobile": user_agent.ch.mobile,
            "sec-ch-ua-model": user_agent.ch.model,
            "sec-ch-ua-platform": user_agent.ch.platform,
            "sec-ch-ua-platform-version": user_agent.ch.platform_version,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-GPC": "1",
            "User-Agent": user_agent.text,
            "X-ASBD-ID": asbd,
            "X-CSRFToken": tokens["csrf_token"],
            "X-IG-App-ID": tokens["app_id"],
            "X-IG-WWW-Claim": "0",
            "X-Requested-With": "XMLHttpRequest",
            "X-Fb-Friendly-Name": "PolarisProfilePageContentQuery",
            "X-Fb-Lsd": tokens["lsd"],
            "X-Web-Device-Id": tokens["device_id"],
        }
        return headers
    
    def fetch_buisnessinfo(self, headers):
        data = {"username": self.username, "hl": "en"}
        try:
            response = self.session.get(self.buisness_url, headers=headers, params=data)
            if response.status_code == 200:
                return response
            else:
                print(f"Failed to fetch buisness info: Status code {response.status_code}")
        except Exception as e:
            print(f"Failed to fetch buisness info: {e}")

    def fetch_userinfo(self, headers, doc_id, tokens):
        data = {
            "av": "0",
            "__d": "www",
            "__user": "0",
            "__a": "1",
            "__req": "1",
            "__hs": tokens["haste_session"],
            "dpr": "1",
            "__ccg": "UNKNOWN",
            "__rev": tokens["revision"],
            "__hsi": tokens["hsi"],
            "__comet_req": tokens["cometreq"],
            "lsd": tokens["lsd"],
            "jazoest": tokens["jazoest"],
            "__spin_r": tokens["revision"],
            "__spin_b": "trunk",
            "__spin_t": tokens["spint"],
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "PolarisProfilePageContentQuery",
            "variables": json.dumps({"id": tokens["user_id"], "render_surface": "PROFILE"}),
            "server_timestamps": "true",
            "doc_id": doc_id
        }
        url = "https://www.instagram.com/api/graphql"
        try:
            response = self.session.post(url, headers=headers, data=data)
            if response.status_code == 200:
                self.save_user_info(response, self.fetch_buisnessinfo(headers))
            else:
                print(f"Failed to fetch user info: Status code {response.status_code}")
        except Exception as e:
            print(f"Failed to fetch user info: {e}")

    def save_user_info(self, response, bresponse):
        try:
            data = response.json().get("data", {}).get("user", {})
            bdata = bresponse.json().get("data", {}).get("user", {})
            bio_links_data = data.get('bio_links', [])
            bio_links = [link['url'] for link in bio_links_data]
            bresp_data = bdata.get('business_address_json', 'Unknown')
            if bresp_data != 'Unknown':
                try:
                    bresp_data = json.loads(bresp_data.replace("\\", ""))
                    bdata['business_address_json'] = bresp_data
                except:
                    bdata['business_address_json'] = bresp_data
            user_data = {
                "full_name": data.get('full_name', 'Unknown'),
                "username": data.get('username', 'Unknown'),
                "id": data.get('id', 'Unknown'),
                "profile_pic_url": data.get('profile_pic_url', 'Unknown'),
                "hd_profile_pic_url": data.get('hd_profile_pic_url_info', {}).get('url', 'Unknown'),
                "follower_count": data.get('follower_count', 'Unknown'),
                "following_count": data.get('following_count', 'Unknown'),
                "media_count": data.get('media_count', 'Unknown'),
                "bio": data.get('biography', 'Unknown'),
                "external_url": data.get('external_url', 'Unknown'),
                "bio_links": bio_links,
                "is_verified": data.get('is_verified', 'Unknown'),
                "is_private": data.get('is_private', 'Unknown'),
                "is_professional_account": bdata.get('is_professional_account', 'Unknown'),
                "business_data": bdata.get('business_address_json', 'Unknown'),
                "is_business": bdata.get('is_business_account', 'Unknown'),
                "category": data.get('category', 'Unknown'),
                "should_show_category": data.get('should_show_category', 'Unknown'),
                "pronouns": data.get('pronouns', 'Unknown')
            }
            with open(f"instagram-{self.username}.json", "w") as f:
                f.write(json.dumps(user_data, indent=4))
            print(f"User info for {self.username} saved successfully.")
        except Exception as e:
            print(f"Failed to save user info: {e}")


if __name__ == "__main__":
    asbd = "129477"
    doc_id = "7412607655516877"
    username = input("Enter username: ")
    scraper = InstagramScraper(username)
    tokens = scraper.fetch_all_tokens()
    if all(tokens.values()):
        headers = scraper.create_meta(tokens, asbd)
        scraper.fetch_userinfo(headers, doc_id, tokens)
    else:
        print("Failed to fetch all required tokens.")
