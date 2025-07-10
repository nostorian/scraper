# github.com/nostorian
# x-scraper (formerly twitter)
import re
import json
from pathlib import Path
from urllib.parse import quote_plus
from datetime import datetime
import ua_generator
from bs4 import BeautifulSoup
from curl_cffi import requests

class Twitter:
    def __init__(self, username: str, save_to_file: bool = False):
       
        self.username = username
        self.session = requests.Session(impersonate="chrome116")
        self.ua_obj = ua_generator.generate(device="desktop", platform="windows", browser="chrome")
        self.save_to_file = save_to_file
        self.api_details = {}
        self.guest_token = None
        self.user_data = {}

    def _get_initial_page(self) -> str:
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "User-Agent": self.ua_obj.text
        }
        try:
            response = self.session.get(f"https://x.com/{self.username}", headers=headers)
            response.raise_for_status()
            return response.text
        except requests.errors.RequestsError as e:
            print(f"Failed to fetch initial page: {e}")
            return None

    def _extract_api_details(self, html_content: str) -> bool:
        soup = BeautifulSoup(html_content, "html.parser")
        js_file_link = soup.find("link", href=re.compile(r"https://abs\.twimg\.com/responsive-web/client-web(-legacy)?/main\..*\.js"))
        if not js_file_link:
            print("Main JS file link not found.")
            return False
            
        js_file_url = js_file_link.get("href")
        try:
            js_response = self.session.get(js_file_url, headers={"Referer": "https://x.com/"})
            js_response.raise_for_status()
            js_content = js_response.text
            bearer_match = re.search(r'Bearer\s+([A-Za-z0-9%]+)', js_content)
            if not bearer_match:
                print("Bearer token not found in JS file.")
                return False
            self.api_details['bearer_token'] = f"Bearer {bearer_match.group(1)}"
            query_match = re.search(r'queryId:"([^"]+)",operationName:"UserByScreenName"', js_content)
            if not query_match:
                print("UserByScreenName Query ID not found.")
                return False
            self.api_details['query_id'] = query_match.group(1)
            
            return True

        except requests.errors.RequestsError as e:
            print(f"Failed to fetch or parse JS file: {e}")
            return False

    def _activate_guest_token(self) -> bool:
        headers = {
            "Authorization": self.api_details['bearer_token'],
            "User-Agent": self.ua_obj.text,
        }
        try:
            response = self.session.post("https://api.x.com/1.1/guest/activate.json", headers=headers)
            response.raise_for_status()
            self.guest_token = response.json().get("guest_token")
            if not self.guest_token:
                print("Could not get guest token from activation response.")
                return False
            return True
        except (requests.errors.RequestsError, json.JSONDecodeError) as e:
            print(f"Failed to activate guest token: {e}")
            return False

    def _fetch_user_data(self) -> dict:
        variables = {"screen_name": self.username, "withSafetyModeUserFields": True}
        features = {
            "responsive_web_grok_bio_auto_translation_is_enabled": False, "hidden_profile_subscriptions_enabled": True,
            "payments_enabled": False, "profile_label_improvements_pcf_label_in_post_enabled": True,
            "rweb_tipjar_consumption_enabled": True, "verified_phone_label_enabled": True,
            "subscriptions_verification_info_is_identity_verified_enabled": True,
            "subscriptions_verification_info_verified_since_enabled": True, "highlights_tweets_tab_ui_enabled": True,
            "responsive_web_twitter_article_notes_tab_enabled": True, "subscriptions_feature_can_gift_premium": True,
            "creator_subscriptions_tweet_preview_api_enabled": True, "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "responsive_web_graphql_timeline_navigation_enabled": True, "responsive_web_graphql_exclude_directive_enabled": True
        }
        
        endpoint = (
            f"https://api.x.com/graphql/{self.api_details['query_id']}/UserByScreenName"
            f"?variables={quote_plus(json.dumps(variables))}"
            f"&features={quote_plus(json.dumps(features))}"
        )
        
        api_headers = {
            "Accept": "*/*",
            "Authorization": self.api_details['bearer_token'],
            "Content-Type": "application/json",
            "Referer": f"https://x.com/{self.username}",
            "User-Agent": self.ua_obj.text,
            "X-Guest-Token": self.guest_token,
            "X-Twitter-Active-User": "yes",
        }
        
        try:
            response = self.session.get(endpoint, headers=api_headers)
            response.raise_for_status()
            return response.json()
        except (requests.errors.RequestsError, json.JSONDecodeError) as e:
            print(f"Failed to retrieve final user data: {e}")
            return None

    def _parse_and_save_data(self, raw_data: dict) -> bool:
        if not raw_data or "data" not in raw_data:
            print("[!] Raw data is empty or malformed.")
            return False
        try:
            user_result = raw_data['data']['user']['result']
            user_core = user_result['core']
            user_legacy = user_result['legacy']
            def get(obj, path, default='N/A'):
                keys = path.split('.')
                for key in keys:
                    if isinstance(obj, dict) and key in obj:
                        obj = obj[key]
                    else:
                        return default
                return obj
            join_date = get(user_core, 'created_at')
            real_join_date = None
            if join_date:
                date_obj = datetime.strptime(join_date, "%a %b %d %H:%M:%S %z %Y")
                real_join_date = date_obj.strftime("%b %d %Y")
            birthdate = user_result['legacy_extended_profile']['birthdate'] if 'legacy_extended_profile' in user_result and 'birthdate' in user_result['legacy_extended_profile'] else None
            parsed_data = {
                "name": get(user_core, 'name'),
                "screen_name": get(user_core, 'screen_name'),
                "user_id": get(user_result, 'rest_id'),
                "avatar_url": get(user_result, 'avatar.image_url', '').replace('_normal', '_400x400'),
                "banner_url": get(user_legacy, 'profile_banner_url'),
                "bio": get(user_legacy, 'description'),
                "website": get(user_legacy, 'url'),
                "location": get(user_result, 'location.location'),
                "birth_date": birthdate if birthdate else 'N/A',
                "join_date": real_join_date,
                "is_verified": get(user_result, 'is_blue_verified'),
                "is_protected": get(user_result, 'privacy.protected'),
                "followers_count": get(user_legacy, 'followers_count'),
                "following_count": get(user_legacy, 'friends_count'),
                "tweets_count": get(user_legacy, 'statuses_count'),
                "likes_count": get(user_legacy, 'favourites_count'),
                "media_count": get(user_legacy, 'media_count'),
            }
            
            self.user_data = parsed_data
            if self.save_to_file:
                output_path = Path(f"x-{self.username}.json")
                output_path.write_text(json.dumps(self.user_data, indent=4), encoding="utf-8")
                return self.user_data
            else:
                return self.user_data
            
        except (KeyError, TypeError) as e:
            print(f"Failed to parse user data from API response: {e}")
            return False

    def scrape(self):
        html_content = self._get_initial_page()
        if not html_content: return
        if not self._extract_api_details(html_content): return
        if not self._activate_guest_token(): return

        raw_data = self._fetch_user_data()
        if not raw_data: return

        a = self._parse_and_save_data(raw_data)
        if not a:
            return "Failed to parse and save user data."
        return a
        


if __name__ == "__main__":
    try:
        user_to_scrape = input("Enter the X username to scrape: ")
        if not user_to_scrape:
            print("Username cannot be empty.")
        else:
            scraper = Twitter(username=user_to_scrape, save_to_file=True)
            scraper.scrape()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
