import requests
from bs4 import BeautifulSoup
import csv
import re
import json

from countryinfo import CountryInfo


# Function to get the continent of each country
def get_continent_for_country(country_name):
    try:
        country_info = CountryInfo(country_name)
        continent = country_info.region()
        return continent
    except Exception as e:
        print(f"Error: {e}")
        return None


# Function to fetch exchange rate data and store it locally
def fetch_exchange_rate_data():
    exchange_rate_url = "https://api.exchangerate-api.com/v4/latest/USD"

    try:
        response = requests.get(exchange_rate_url)
        if response.status_code == 200:
            data = response.json()
            with open('exchange_rate_data.json', 'w') as json_file:
                json.dump(data, json_file)
            return data
        else:
            print("Failed to fetch exchange rate data. Status code:", response.status_code)
            return None
    except Exception as e:
        print(f"Error fetching exchange rate data: {str(e)}")
        return None


# Function to load exchange rate data from a local file
def load_exchange_rate_data():
    try:
        with open('exchange_rate_data.json', 'r') as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        print("Exchange rate data file not found. Fetching data...")
        return fetch_exchange_rate_data()
    except Exception as e:
        print(f"Error loading exchange rate data: {str(e)}")
        return None


# Function to fetch exchange rate from XE.com
def fetch_exchange_rate_from_xe(amount, currency):
    try:
        xe_url = f"https://www.xe.com/currencyconverter/convert/?Amount={amount}&From={currency}&To=USD"
        response = requests.get(xe_url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract exchange rate information from XE.com
            exchange_rate_tag = soup.find('p', class_='result__BigRate-sc-1bsijpp-1 iGrAod')
            if exchange_rate_tag:
                exchange_rate_text = exchange_rate_tag.text.strip()
                # Extract the numeric part of the exchange rate
                exchange_rate_numeric = exchange_rate_text.split(' ')[0]
                # Convert it to a float
                exchange_rate = float(exchange_rate_numeric.replace(',', ''))
                return exchange_rate
            else:
                print(f"Exchange rate for {currency} not found on XE.com.")
                return None
        else:
            print(f"Failed to fetch exchange rate for {currency} from XE.com. Status code:", response.status_code)
            return None
    except Exception as e:
        print(f"Error fetching exchange rate for {currency} from XE.com: {str(e)}")
        return None


# Function to convert salary in local currency to US dollars
def convert_currency_to_usd(amount, currency, exchange_rate_data):
    if currency in exchange_rate_data["rates"]:
        exchange_rate = exchange_rate_data["rates"][currency]
        usd_amount = float(amount) / exchange_rate
        return round(usd_amount, 2)
    else:
        try:
            print(f"getting {currency} for ex")
            exchange_rate = fetch_exchange_rate_from_xe(amount, currency)
            return exchange_rate
        except Exception as e:
            print(f"Error fetching exchange rate for {currency} from another source: {str(e)}")


# Function to scrape salary information for a given country URL
def scrape_country_salary_info(country_url, exchange_rate_data):
    response = requests.get(country_url, allow_redirects=False)

    if response.status_code == 302:
        # The response is a redirect
        redirect_url = response.headers['Location']
        # Make another request to the new URL
        response = requests.get(redirect_url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check for "Average Monthly Salary" or "Average Yearly Salary" text on the page
        page_text = soup.get_text()

        if "Average Monthly Salary" in page_text:
            wage_span = "Monthly"
        elif "Average Yearly Salary" in page_text:
            wage_span = "Yearly"
        else:
            wage_span = "N/A"

        # Extracting salary information
        salary_block = soup.find('div', class_='salaryblock')
        average_salary_text = salary_block.find('span', class_='average').find('b').text.strip()
        lowest_salary_text = salary_block.find('span', class_='lowest').find('b').text.strip()
        highest_salary_text = salary_block.find('span', class_='highest').find('b').text.strip()

        td_elements = soup.find_all('td')
        median_salary_text = td_elements[1].get_text()

        # Extract currency
        currency = soup.select_one('span.average b + br').next_sibling.strip()

        # Extract numeric salary values
        average_salary = re.sub(r'[^\d.]', '', average_salary_text)
        lowest_salary = re.sub(r'[^\d.]', '', lowest_salary_text)
        highest_salary = re.sub(r'[^\d.]', '', highest_salary_text)
        median_salary = re.sub(r'[^\d.]', '', median_salary_text)

        # Convert yearly salary to monthly basis if needed
        if wage_span == "Yearly":
            average_salary = convert_yearly_to_monthly(average_salary)
            lowest_salary = convert_yearly_to_monthly(lowest_salary)
            highest_salary = convert_yearly_to_monthly(highest_salary)
            median_salary = convert_yearly_to_monthly(median_salary)

        # Convert local currency salaries to USD
        if currency != "USD":
            usd_average_salary = convert_currency_to_usd(average_salary, currency, exchange_rate_data)
            usd_lowest_salary = convert_currency_to_usd(lowest_salary, currency, exchange_rate_data)
            usd_highest_salary = convert_currency_to_usd(highest_salary, currency, exchange_rate_data)
            usd_median_salary = convert_currency_to_usd(median_salary, currency, exchange_rate_data)

            if usd_average_salary is not None and usd_lowest_salary is not None and usd_highest_salary is not None:
                return {
                    'wage_span': "Monthly",  # Converted to monthly basis
                    'average_salary': usd_average_salary,
                    'lowest_salary': usd_lowest_salary,
                    'highest_salary': usd_highest_salary,
                    'median_salary': usd_median_salary
                }
            else:
                print(f"Currency conversion failed for {currency}. Using original values.")

        return {
            'wage_span': "Monthly",  # Converted to monthly basis
            'average_salary': average_salary,
            'lowest_salary': lowest_salary,
            'highest_salary': highest_salary,
            'median_salary': median_salary
        }
    else:
        print(f"Failed to retrieve data for {country_url}. Status code:", response.status_code)
        return None


# Function to scrape country names and links from the main page
def scrape_country_names_and_links():
    url = "https://www.salaryexplorer.com/#browsesalaries"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all <b> elements
        country_elements = soup.find_all('b')

        country_data = []

        for country_element in country_elements:
            country_link = country_element.find('a')

            if country_link:
                country_name = country_link.text.strip()
                country_link_url = country_link['href']
                country_data.append({'country_name': country_name, 'country_link': country_link_url})

        return country_data
    else:
        print("Failed to retrieve the main page. Status code:", response.status_code)
        return None


# Function to convert yearly salary to monthly
def convert_yearly_to_monthly(yearly_salary):
    # Assuming 12 months in a year
    return str(int(float(yearly_salary) / 12))


# Function to log country data to a CSV file
def log_country_data_to_csv(country_data, exchange_rate_data):
    salary_data_list = []

    if country_data:
        total_countries = len(country_data)

        for idx, country in enumerate(country_data, start=1):
            country_url = country['country_link']
            salary_info = scrape_country_salary_info(country_url, exchange_rate_data)
            continent = get_continent_for_country(country['country_name'])

            if salary_info:
                salary_data = {
                    'country_name': country['country_name'],
                    'continent_name': continent,
                    'wage_span': salary_info['wage_span'],
                    'median_salary': salary_info['median_salary'],
                    'average_salary': salary_info['average_salary'],
                    'lowest_salary': salary_info['lowest_salary'],
                    'highest_salary': salary_info['highest_salary']
                }
                salary_data_list.append(salary_data)

            # Print loading progress
            print(f"Processed {idx}/{total_countries} countries.")

        # Define the CSV file name
        csv_filename = 'salary_data.csv'

        # Write data to the CSV file
        with open(csv_filename, mode='w', newline='') as csv_file:
            fieldnames = ['country_name', 'continent_name', 'wage_span', 'median_salary', 'average_salary', 'lowest_salary',
                          'highest_salary']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for salary_data in salary_data_list:
                writer.writerow(salary_data)

        print(f"Data has been saved to {csv_filename}.")
    else:
        print("No data to save.")
