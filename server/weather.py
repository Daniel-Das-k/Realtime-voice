import requests

def get_weather(params):
    """Get current weather information for a city using OpenWeatherMap API."""
    # city = params.get('city')
    api_key = params.get('api_key', 'b2587aab605c990a19de370e029f7629')  # Default API key
    
    if not city:
        return {"error": "City parameter is required"}
    
    url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        weather_info = {
            'city': city,
            'description': data['weather'][0]['description'].capitalize(),
            'temperature': round(data['main']['temp'], 1),
            'feels_like': round(data['main']['feels_like'], 1),
            'humidity': data['main']['humidity'],
            'pressure': data['main']['pressure'],
            'wind_speed': data['wind']['speed'],
            'clouds': data['clouds']['all'],
            'timestamp': data['dt'],
            'sunrise': data['sys']['sunrise'],
            'sunset': data['sys']['sunset']
        }
        return weather_info
    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching weather data: {str(e)}"}
    except KeyError as e:
        return {"error": f"Error parsing weather data: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def display_weather(weather_info):
    """Print weather information in a user-friendly format."""
    if "error" in weather_info:
        print(f"\nError: {weather_info['error']}")
        return
        
    print(f"\nCurrent Weather in {weather_info['city']}:")
    print(f"Conditions: {weather_info['description']}")
    print(f"Temperature: {weather_info['temperature']}°C")
    print(f"Feels Like: {weather_info['feels_like']}°C")
    print(f"Humidity: {weather_info['humidity']}%")
    print(f"Pressure: {weather_info['pressure']} hPa")
    print(f"Wind Speed: {weather_info['wind_speed']} m/s")
    print(f"Cloud Coverage: {weather_info['clouds']}%")

def main():
    # Example usage
    params = {
        'city': 'Chennai',
        'api_key': 'b2587aab605c990a19de370e029f7629'
    }
    
    weather_info = get_weather(params)
    display_weather(weather_info)

if __name__ == "__main__":
    main()