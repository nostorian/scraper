# github.com/nostorian
# github-scraper
import requests
import json

class GitHubUserScraper:
    def __init__(self, username, save_to_file=False):
        self.username = username
        self.url = f"https://api.github.com/users/{username}"
        self.data = None
        self.save_to_file = save_to_file

    def fetch_user_data(self):
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            self.data = response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"An error occurred: {req_err}")

    def save_data_to_file(self):
        if self.data:
            if self.save_to_file:
                with open(f"github-{self.username}.json", "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=4)
                return self.data
            else:
                return self.data
        else:
            print("No data to save.")

    def run(self):
        self.fetch_user_data()
        self.save_data_to_file()

if __name__ == "__main__":
    username = input("Enter username to scrape: ")
    scraper = GitHubUserScraper(username)
    scraper.run()
