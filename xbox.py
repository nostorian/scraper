# github.com/nostorian
# xbox-scraper
import requests
import json

class XboxUserLookup:
    def __init__(self, auth_token, save_to_file=False):
        self.base_url = "https://peoplehub.xboxlive.com/users/me/people"
        self.save_to_file = save_to_file
        self.headers = {
            "accept": "application/json",
            "Accept-Encoding": "gzip",
            "accept-language": "en-US",
            "authorization": auth_token,
            "Connection": "Keep-Alive",
            "Host": "peoplehub.xboxlive.com",
            "User-Agent": "okhttp/4.9.2",
            "x-xbl-contract-version": "5"
        }

    def xuid_lookup(self, gamer_tag):
        try:
            response = requests.get(
                f"{self.base_url}/search/decoration/detail,preferredColor?q={gamer_tag}&maxItems=15",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("people"):
                raise ValueError("Gamertag not found")
            return data["people"][0]["xuid"]
        except requests.exceptions.RequestException as e:
            print(f"An error occurred during XUID lookup: {e}")
        except ValueError as e:
            print(e)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        return None

    def user_lookup(self, xuid, gamer_tag):
        try:
            response = requests.get(
                f"{self.base_url}/xuids({xuid})/decoration/detail,preferredColor,presenceDetail,multiplayerSummary",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            person = data['people'][0]

            def get_value(data, keys, default='Unknown'):
                for key in keys:
                    data = data.get(key, {})
                return data if data else default
            

            user_info = {
                "XUID": xuid,
                "Gamertag": get_value(person, ['gamertag']),
                "Display Name": get_value(person, ['displayName']),
                "Modern Gamertag": get_value(person, ['modernGamertag']),
                "Modern Gamertag Suffix": get_value(person, ['modernGamertagSuffix']),
                "Unique Modern Gamertag": get_value(person, ['uniqueModernGamertag']),
                "Real Name": get_value(person, ['realName']),
                "Display Picture": get_value(person, ['displayPicRaw']),
                "Gamer Score": get_value(person, ['gamerScore']),
                "Xbox One Rep": get_value(person, ['xboxOneRep']),
                "Presence Text": get_value(person, ['presenceText']),
                "Presence State": get_value(person, ['presenceState']),
                "Follower Count": get_value(person, ['detail', 'followerCount']),
                "Following Count": get_value(person, ['detail', 'followingCount']),
                "Linked Accounts": [
                    {
                        "Network Name": get_value(account, ['networkName']),
                        "Display Name": get_value(account, ['displayName']),
                        "Deeplink": get_value(account, ['deeplink'])
                    } for account in person.get('linkedAccounts', [])
                ] or "No linked accounts",
                "Bio": get_value(person, ['detail', 'bio']),
                "Location": get_value(person, ['detail', 'location']),
                "Tenure": get_value(person, ['detail', 'tenure']),
                "Has Game Pass": get_value(person, ['detail', 'hasGamePass'], False),
                "Color Theme": get_value(person, ['colorTheme']),
                "Preferred Platforms": get_value(person, ['preferredPlatforms'])
            }

            if self.save_to_file:
                with open(f"xbox-{gamer_tag}_info.json", "w") as file:
                    json.dump(user_info, file, indent=4)
                return user_info
            else:
                return user_info

        except requests.exceptions.RequestException as e:
            print(f"An error occurred during user lookup: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    auth_token = "Enter your XBL 3.0 Authorization Token here"
    gamer_tag = input("Enter gamertag of user to scrape: ")

    xbox_lookup = XboxUserLookup(auth_token, save_to_file=False)

    xuid = xbox_lookup.xuid_lookup(gamer_tag)
    if xuid:
        print(f"Fetched XUID of {gamer_tag}: {xuid}")
        xbox_lookup.user_lookup(xuid, gamer_tag)
