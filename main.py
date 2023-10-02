from scrape_salaries import log_country_data_to_csv, scrape_country_names_and_links, load_exchange_rate_data

if __name__ == "__main__":
    # Load exchange rate data from a local file or fetch it if not available
    exchange_rate_data = load_exchange_rate_data()

    # Scrape country names and links
    country_data = scrape_country_names_and_links()

    if country_data:
        # Log country data to a CSV file
        log_country_data_to_csv(country_data, exchange_rate_data)
    else:
        print("No data to save.")
