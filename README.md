# Finance1: An Educational Stock Trading Application

Finance1 is an educational platform that allows users to learn about stock trading by investing with virtual money. Users can buy, sell, and look up real-time stock prices displayed with interactive candlestick graphs.

**Live Demo:** [https://finance1-wine.vercel.app/](https://finance1-wine.vercel.app/)


## Features

- **User Authentication**: Register, login, and password management
- **Portfolio Management**: Track owned stocks and current values
- **Real-time Stock Data**: Look up current stock prices and historical data
- **Stock Trading**: Buy and sell stocks with virtual currency
- **Transaction History**: View all past trading activities
- **Interactive Visualizations**: Candlestick charts for stock price analysis

## How It's Made

### Tech Stack

- **Backend**: Flask (Python)
- **Database**: MongoDB
- **Frontend**: HTML, CSS, JavaScript
- **CSS Framework**: Bootstrap
- **Data Visualization**: Plotly (for candlestick charts)
- **API Integration**: Real-time stock data API

### Project Structure

```
finance1/
├── app.py              # Main Flask application server
├── helpers.py          # Helper functions (lookup, usd formatting, etc.)
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not included in repo)
├── static/             # Static assets
│   ├── styles.css      # CSS file
│   └── favicon.ico/    # Icon
└── templates/          # HTML templates
    ├── layout.html     # Base template
    ├── index.html      # Portfolio dashboard
    ├── buy.html        # Stock purchase form
    ├── sell.html       # Stock selling form
    ├── quote.html      # Stock lookup form
    ├── quoted.html     # Stock quote display with graph
    ├── history.html    # Transaction history
    ├── register.html   # User registration
    ├── login.html      # User login
    ├── change.html     # Password change form
    └── apology.html    # Error Page
```

### Key Components

#### Backend (Flask)

The application uses Flask to handle HTTP requests and render templates. Key routes include:

- `/` - Display user's portfolio
- `/buy` - Purchase stocks
- `/sell` - Sell owned stocks
- `/quote` - Look up stock prices
- `/history` - View transaction history
- `/register`, `/login`, `/logout` - User authentication
- `/changepassword` - Update user credentials

#### Database (MongoDB)

The application uses MongoDB to store:

- User information (username, password hash, cash balance)
- Stock ownership data
- Transaction history
- Session information

#### Data Visualization

Stock price data is visualized using candlestick charts, which show opening, closing, high, and low prices over time.

## Setup and Installation

### Prerequisites

- Python 3.8+
- MongoDB
- API key for stock data (set in .env file)

### Installation Steps

1. Clone the repository
   ```
   git clone https://github.com/yourusername/finance1.git
   cd finance1
   ```

2. Install dependencies
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with the following variables:
   ```
   mongodb_conn_str=<your_mongodb_connection_string>
   SECRET_KEY=<your_secret_key>
   API_KEY=<your_stock_api_key>
   ```

4. Run the application
   ```
   flask run
   ```

5. Open your browser and navigate to `http://localhost:5000`

## Learning Objectives

This project helps users learn:

- Basic stock market concepts
- How to read stock charts
- Portfolio management
- Investment decision-making
- Risk assessment without real financial loss

## Future Enhancements

- Add educational resources about investing
- Implement mock news events that affect stock prices
- Create leaderboards for user performance

## Acknowledgments

- Stock data provided by [Alpha Vantage]
- Inspired by CS50's Finance problem set
