# github.com/nostorian
# reddit-scraper
from curl_cffi import requests
import json
from bs4 import BeautifulSoup
import json

class RedditScraper:
    def __init__(self, username, save_to_file=False):
        self.username = username
        self.save_to_file = save_to_file
        self.base_url = f"https://www.reddit.com/user/{username}/"
        self.session = requests.Session(impersonate="chrome136")
        self.soup = None

    def fetch_page(self, url):
        try:
            response = self.session.get(url)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 302:
                redirected_url = f"https://www.reddit.com{response.headers['Location']}"
                print(f"Redirected to {redirected_url}")
                response = self.session.get(redirected_url)
                if response.status_code == 200:
                    return response.text
            print(f"Error fetching the page: Status code {response.status_code}")
            return None
        except Exception as e:
            print(f"Error fetching the page: {e}")
            return None

    def parse_page(self, page_content):
        try:
            return BeautifulSoup(page_content, "html.parser")
        except Exception as e:
            print(f"Error parsing the page content: {e}")
            return None

    def extract_info(self, soup):
        try:
            title = soup.find("shreddit-title", {"title": True})["title"]
            name = title.split(" - ")[0].split(" (")[0]
            username = f"u/{title.split(' - ')[0].split(' (')[1].replace('u/', '').replace(')', '')}"
            
            karma = soup.find_all("span", {"data-testid": "karma-number"})
            post_karma = karma[0].text.strip() if karma else None
            comment_karma = karma[1].text.strip() if len(karma) > 1 else None
            
            cake_day = soup.find("time", {"data-testid": "cake-day"}).text.strip() if soup.find("time", {"data-testid": "cake-day"}) else None
            bio = soup.find("p", {"data-testid": "profile-description"}).text.strip() if soup.find("p", {"data-testid": "profile-description"}) else None
            
            trophies = soup.find("shreddit-profile-trophy-list").find_all("li") if soup.find("shreddit-profile-trophy-list") else None
            trophies = [trophy.text.strip() for trophy in trophies] if trophies else None
            proper_trophies = [{"name": t.split("\n")[0], "description": t.split("\n")[1]} if "\n" in t else t for t in trophies] if trophies else None
            
            followers = None
            flex_cols = soup.find_all("div", {"class": "flex flex-col min-w-0"})
            if len(flex_cols) > 2:
                followers_elem = flex_cols[2].find("p", {"class": "m-0 text-neutral-content-strong text-14 font-semibold whitespace-nowrap"})
                if followers_elem:
                    followers = followers_elem.text.strip()
            
            moderator_communities = soup.find("ul", {"role": "menu"}).find_all("a") if soup.find("ul", {"role": "menu"}) else None
            moderator_communities = [community.text.strip().split("\n")[0] for community in moderator_communities] if moderator_communities else None
            
            faceplate_partial = soup.find("faceplate-partial", {"loading": "action", "src": True})
            extra_moderator_communities = self.get_extra_moderator_communities(faceplate_partial["src"].strip()) if faceplate_partial else None
            
            complete_mod_communities = moderator_communities + extra_moderator_communities if moderator_communities and extra_moderator_communities else moderator_communities if moderator_communities else extra_moderator_communities
            
            trackers = soup.find_all("faceplate-tracker", {"noun": "social_link"})
            links = self.extract_social_links(trackers)
            pageData = soup.find("reddit-page-data")
            if pageData:
                avatarRaw = json.loads(pageData["data"]).get("profile", {}).get("icon")
                avataralmostDone = avatarRaw.split("?")[0] if avatarRaw else None
                if avataralmostDone.startswith("https://preview.redd.it"):
                    splitAvatar = avataralmostDone.split("https://preview")[1]
                    avatar = f"https://i{splitAvatar}" if splitAvatar else None
                else:
                    avatar = avataralmostDone

                isNsfw = json.loads(pageData["data"]).get("profile", {}).get("isNsfw")
                if isNsfw:
                    nsfwStatus = True
                else:
                    nsfwStatus = False
            else:
                avatar = None
                nsfwStatus = False
            return {
                "avatar": avatar,
                "name": name,
                "username": username,
                "followers": followers,
                "post_karma": post_karma,
                "comment_karma": comment_karma,
                "nsfw_status": nsfwStatus,
                "cake_day": cake_day,
                "bio": bio,
                "trophies": proper_trophies,
                "moderator_communities": complete_mod_communities,
                "links": links
            }
        except Exception as e:
            print(f"Error extracting information: {e}")
            return None

    def get_extra_moderator_communities(self, extra_moderator_request_url):
        try:
            extra_moderator_request = self.session.get(f"https://www.reddit.com{extra_moderator_request_url}")
            if extra_moderator_request.status_code == 200:
                mod_soup = BeautifulSoup(extra_moderator_request.text, "html.parser")
                menu = mod_soup.find("ul", {"role": "menu"})
                if menu:
                    extra_moderator_communities = menu.find_all("a")
                    return [community.text.strip().split("\n")[0] for community in extra_moderator_communities]
            print(f"Error fetching extra moderator communities: Status code {extra_moderator_request.status_code}")
            return None
        except Exception as e:
            print(f"Error fetching extra moderator communities: {e}")
            return None

    def extract_social_links(self, trackers):
        links = []
        if trackers:
            for tracker in trackers:
                data = tracker.get("data-faceplate-tracking-context")
                if data:
                    try:
                        context = json.loads(data)
                        social_link = context.get("social_link", {})
                        link_type = social_link.get("type")
                        link_url = social_link.get("url")
                        link_name = social_link.get("name")
                        if link_type and link_url and link_name:
                            links.append({"type": link_type, "url": link_url, "name": link_name})
                    except json.JSONDecodeError:
                        pass
        return links

    def save(self, data, filename):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving to file: {e}")

    def run(self):
        page_content = self.fetch_page(self.base_url)
        if page_content:
            soup = self.parse_page(page_content)
            if soup:
                user_info = self.extract_info(soup)
                if user_info and self.save_to_file:
                    self.save(user_info, f"reddit-{self.username}.json")
                    return user_info
                elif user_info:
                    return user_info
                else:
                    print("Failed to extract user information.")
            else:
                print("Failed to parse page content.")
        else:
            print("Failed to fetch page content.")

if __name__ == "__main__":
    username = input("Enter username to scrape: ")
    scraper = RedditScraper(username, save_to_file=True)
    scraper.run()
