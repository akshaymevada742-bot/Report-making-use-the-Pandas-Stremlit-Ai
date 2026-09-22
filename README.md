# 🛒 E-Commerce Sales Analytics + Local AI

An interactive **E-Commerce Sales Analytics Dashboard** built with **Streamlit, Pandas, Plotly, PandasAI, LiteLLM, and Ollama**.

The application combines traditional business analytics with a **local AI data analyst**, allowing users to explore sales data, generate business insights, forecast future revenue, and ask questions about the dataset using a locally running LLM.

> 🤖 **No OpenAI API is required.** The application uses local **Ollama + llama3.2** for AI-powered data analysis.

---

## 📊 Project Overview

This project provides an interactive dashboard for analyzing e-commerce sales data.

The dashboard includes:

* 💰 Revenue analysis
* 📦 Order analysis
* ⭐ Customer rating analysis
* 🚚 Delivery performance
* 🏷️ Discount impact analysis
* 🌍 Regional analysis
* 💳 Payment method analysis
* 📅 Monthly revenue trends
* 🏆 Customer and category leaderboards
* 📆 Year-over-Year analysis
* 📈 Period-over-period comparison
* 🔮 Future revenue prediction
* 🎯 Data-driven areas to focus
* 🤖 AI-powered data analysis
* 📤 CSV and Excel export
* 🎨 Dark/Light dashboard theme

The application loads the e-commerce CSV dataset and converts `order_date` into a datetime field for analysis.

---

# ✨ Features

## 🎨 1. Dark / Light Theme

The dashboard supports two themes:

```text
🌙 Dark
☀️ Light
```

Users can select the dashboard theme from the sidebar.

Plotly charts automatically switch between:

```text
plotly_dark
plotly_white
```

based on the selected theme.

---

## 🔎 2. Interactive Filters

Users can filter the dashboard by:

### Product Category

Multiple product categories can be selected.

### Region

Multiple regions can be selected.

### Date Range

The dashboard provides separate:

```text
📅 Start Date
📅 End Date
```

selectors.

Users can also reset the date selection using:

```text
↺ Reset dates
```

---

# 📌 KPI Dashboard

The dashboard displays four main KPIs:

| KPI                      | Description                         |
| ------------------------ | ----------------------------------- |
| 💰 Total Revenue         | Total revenue for the selected data |
| 📦 Total Orders          | Number of orders                    |
| ⭐ Average Rating         | Average customer rating             |
| 🚚 Average Delivery Days | Average delivery time               |

These KPIs are calculated from the currently filtered dataset.

---

# 📊 Sales Analysis

## 💰 Revenue by Product Category

The application groups revenue by:

```text
product_category
```

and displays the results using a Plotly bar chart.

Categories are sorted from highest to lowest revenue.

---

## 🌍 Revenue by Region

Revenue can be analyzed across different regions.

The dashboard calculates:

```text
Region → Total Revenue
```

and displays the result as a bar chart.

---

## 💳 Revenue by Payment Method

The application analyzes revenue generated through different payment methods.

A Plotly pie chart is used to visualize the distribution.

---

# 📈 Monthly Revenue Trend

The application aggregates revenue by month and displays a time-series line chart.

The monthly analysis helps identify:

* Revenue trends
* Increasing/decreasing periods
* Seasonal patterns
* Changes in sales performance

The application resamples the transaction data using monthly periods.

---

# 🏆 Top-N Leaderboard

The dashboard includes a configurable **Top-N Leaderboard**.

Users can select between:

```text
3 → 25
```

top entries.

## 👤 Top Customers

Customers are ranked using:

* Total Revenue
* Number of Orders
* Average Rating

## 📦 Top Categories

Categories are ranked using:

* Total Revenue
* Units Sold
* Orders
* Average Rating

---

# 📆 Year-over-Year Analysis

The dashboard compares revenue across calendar years.

It calculates:

```text
Revenue
Orders
Average Rating
YoY Growth %
```

The application also attempts to distinguish complete years from a potentially partial latest year before drawing full-history growth conclusions.

---

# 🚚 Delivery Performance

Users can select a:

```text
Late delivery threshold
```

The application then calculates whether an order is considered late:

```python
delivery_days > late_threshold
```

The dashboard displays:

* Average delivery days
* Late-order percentage
* Late-delivery rate by region

---

# 🏷️ Discount Impact Analysis

The application divides discounts into four groups:

```text
0–10%
10–20%
20–30%
30%+
```

It calculates:

* Orders
* Average order revenue
* Total discount given
* Average customer rating

The dashboard visualizes:

```text
Average Order Revenue by Discount Tier
Average Customer Rating by Discount Tier
```

The application explicitly notes that the dataset does not contain cost/margin information, so this analysis focuses on realized revenue and rating rather than true profit margin.

---

# 🔄 Period-over-Period Comparison

The selected date range is compared against the immediately preceding period of the same length.

For example:

```text
Selected Period
01-Jan → 31-Jan

Compared With
01-Dec → 31-Dec
```

The application compares:

* Revenue
* Orders
* Average Rating

This allows the selected date range to directly affect the business comparison.

---

# 💡 Business Insights & Alerts

The dashboard automatically generates data-driven business insights based on the current filters.

Examples include:

* Revenue growth/decline
* Category concentration
* Regional differences
* Delivery risks
* Payment-channel concentration
* Discount effectiveness
* Customer-rating alerts

The insights are calculated from the dashboard's actual aggregations rather than static text.

---

# 🔮 Future Revenue Prediction

The application includes a **Future Revenue Prediction** module.

Users can select a forecast horizon between:

```text
3 → 12 months
```

The model uses historical monthly revenue and combines:

* Time trend
* Calendar month
* Month-of-year seasonality

When available, the application uses:

```text
sklearn.linear_model.LinearRegression
```

If that model cannot be used, the application falls back to a linear trend calculation using NumPy.

---

## 📈 Actual vs Predicted Revenue

The dashboard compares:

```text
Actual Monthly Revenue
        vs
Predicted Monthly Revenue
```

It also displays:

* Last actual monthly revenue
* Next month's predicted revenue
* Forecast for the selected number of months
* Expected percentage change

> ⚠️ Forecast values are estimates and should not be treated as guarantees.

---

# 🎯 Areas to Focus

The application automatically identifies potential areas requiring attention.

The analysis considers:

### Product Category

Compares the leading and lowest-revenue categories.

### Region

Identifies regional revenue gaps.

### Delivery

Identifies regions with higher late-delivery rates.

### Discount Strategy

Compares discount tiers using average order revenue and customer ratings.

### Future Growth

Uses the forecast to identify potential future growth or decline signals.

---

# 📤 Export Data

Users can export the filtered dataset in three formats:

### CSV

```text
filtered_sales_data.csv
```

### Excel

```text
filtered_sales_data.xlsx
```

### Summary Report

```text
sales_summary_report.txt
```

The summary report includes:

* Selected filters
* Date range
* Total revenue
* Total orders
* Average rating
* Average delivery days
* Top category
* Top region
* Top payment method

---

# 🤖 Local AI Data Analyst

One of the main features of this project is the integrated **PandasAI + Ollama** data analyst.

The application uses:

```text
Streamlit
      ↓
PandasAI
      ↓
LiteLLM
      ↓
Ollama
      ↓
llama3.2
```

The application is configured to use:

```text
http://localhost:11434
```

with:

```text
ollama/llama3.2
```

---

# 💬 Ask Your Data

Users can ask questions directly about the e-commerce dataset.

Example questions included in the application:

```text
Total revenue by product category?

Highest revenue category?

Revenue by region?

Average customer rating?

Top payment method by revenue?

Show monthly revenue
```

---

# ⚡ Fast AI Query Path

Common questions are answered directly from already-calculated dashboard aggregations.

This avoids unnecessarily sending simple questions to the local LLM.

For example:

```text
Revenue by region
```

can be answered using the existing region aggregation.

Similarly:

```text
Highest revenue category
```

can use the existing category revenue calculation.

This provides a faster response for common questions.

---

# 🧠 PandasAI Integration

For questions that cannot be handled by the fast path, the application creates a PandasAI DataFrame and sends the question to the configured local LLM.

The application also maintains:

```text
Chat History
Question Cache
PandasAI Cache
```

to reduce unnecessary repeated processing.

---

# ⚡ Performance Optimization

Several performance optimizations are included.

## Streamlit Data Cache

The CSV loading function uses:

```python
@st.cache_data
```

to avoid repeatedly loading the same dataset.

## Cached Filtered Data

Filtered data is cached based on:

```text
Category
Region
Start Date
End Date
```

## Cached Aggregations

Several expensive calculations use:

```python
@st.cache_data
```

including:

* Category revenue
* Region revenue
* Payment revenue
* Monthly revenue
* Leaderboards
* Yearly summary
* Forecasting
* Period comparison

## Cached AI Configuration

The Ollama/PandasAI configuration uses:

```python
@st.cache_resource
```

so the LLM configuration is not recreated on every interaction.

---

# 🛠️ Technologies Used

| Technology         | Purpose                  |
| ------------------ | ------------------------ |
| **Python**         | Application development  |
| **Streamlit**      | Interactive dashboard    |
| **Pandas**         | Data manipulation        |
| **Plotly Express** | Interactive charts       |
| **PandasAI**       | AI-powered data analysis |
| **LiteLLM**        | LLM interface            |
| **Ollama**         | Local LLM runtime        |
| **llama3.2**       | Local AI model           |
| **Scikit-learn**   | Revenue forecasting      |
| **NumPy**          | Forecast fallback        |
| **OpenPyXL**       | Excel export             |

---

# 📁 Project Structure

A recommended GitHub repository structure is:

```text
E-Commerce-Sales-Analytics/
│
├── app8_future_prediction_fast_theme.py
│
├── E-Commerce Sales Analytics.csv
│
├── README.md
│
├── screenshots/
│   └── dashboard.png
│
└── requirements.txt
```

---

# ⚙️ Installation

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/e-commerce-sales-analytics.git
```

Move into the project directory:

```bash
cd e-commerce-sales-analytics
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

---

## 3. Install Dependencies

Create a `requirements.txt` file containing the required packages.

```text
streamlit
pandas
plotly
pandasai
pandasai-litellm
litellm
ollama
scikit-learn
numpy
openpyxl
```

Then install:

```bash
pip install -r requirements.txt
```

---

# 🦙 Ollama Setup

Install Ollama on your computer and make sure the Ollama service is running.

Pull the model used by this application:

```bash
ollama pull llama3.2
```

Test it:

```bash
ollama run llama3.2
```

The application expects Ollama at:

```text
http://localhost:11434
```

and uses:

```text
ollama/llama3.2
```

as the configured model.

---

# ▶️ Run the Application

Start Streamlit using:

```bash
streamlit run app8_future_prediction_fast_theme.py
```

Streamlit will provide a local address such as:

```text
http://localhost:8501
```

Open that address in your browser.

---

# 📂 Dataset Configuration

The current Python application uses the following local CSV path:

```python
FILE_PATH = r"D:\E-Commerce Sales Analytics.csv"
```

For GitHub, it is recommended to change this to a repository-relative path, for example:

```python
FILE_PATH = "data/E-Commerce Sales Analytics.csv"
```

Then structure the repository as:

```text
project/
│
├── app8_future_prediction_fast_theme.py
├── README.md
│
└── data/
    └── E-Commerce Sales Analytics.csv
```

---

# 📋 Expected Dataset Columns

The application expects fields including:

```text
order_id
order_date
customer_id
product_category
region
quantity
unit_price
discount
payment_method
delivery_days
customer_rating
revenue
```

The application uses these fields for filtering, KPIs, charts, forecasting, delivery analysis, discount analysis, and AI questions.

---

# 💬 Example AI Questions

After starting the application, try:

```text
What is the total revenue by product category?
```

```text
Which category has the highest revenue?
```

```text
Show revenue by region.
```

```text
What is the average customer rating?
```

```text
Which payment method generates the most revenue?
```

```text
Show monthly revenue.
```

---

# 🔧 Troubleshooting

## Streamlit Not Recognized

If you see:

```text
'streamlit' is not recognized as an internal or external command
```

try:

```bash
python -m streamlit run app8_future_prediction_fast_theme.py
```

---

## PandasAI Not Found

If you see:

```text
ModuleNotFoundError: No module named 'pandasai'
```

install:

```bash
pip install pandasai pandasai-litellm
```

Make sure you install them inside the same Python environment used to run Streamlit.

---

## Ollama Connection Error

Make sure Ollama is running.

Test:

```bash
ollama list
```

You should see:

```text
llama3.2
```

If it is not installed:

```bash
ollama pull llama3.2
```

---

## Excel Export Not Working

Install:

```bash
pip install openpyxl
```

The application uses OpenPyXL when generating Excel downloads.

---

# 📸 Dashboard Screenshot

Add your dashboard screenshot to:

```text
screenshots/dashboard.png
```

Then add this to the README:

```markdown
![E-Commerce Sales Analytics Dashboard](screenshots/dashboard.png)
```

---

# 🔐 Local AI & Privacy

The AI component is designed around a local Ollama server:

```text
Streamlit
    ↓
PandasAI
    ↓
LiteLLM
    ↓
Ollama
    ↓
Local LLM
```

The application footer identifies the setup as:

```text
Local AI | Ollama llama3.2 | PandasAI | No OpenAI API required
```

---

# 🚀 Future Improvements

Possible future enhancements include:

* [ ] Add authentication
* [ ] Add database connectivity
* [ ] Add automated data refresh
* [ ] Add more forecasting models
* [ ] Add advanced time-series models
* [ ] Add product-level analysis
* [ ] Add customer segmentation
* [ ] Add RFM analysis
* [ ] Add geographic visualization
* [ ] Add anomaly detection
* [ ] Add downloadable dashboard reports
* [ ] Add more AI-powered questions
* [ ] Deploy the application online

---

# 🎓 Skills Demonstrated

This project demonstrates practical experience with:

* Python
* Streamlit
* Pandas
* Plotly
* Data Cleaning
* Exploratory Data Analysis
* Data Visualization
* KPI Development
* Business Analytics
* Time-Series Analysis
* Forecasting
* Customer Analytics
* Regional Analysis
* Delivery Analytics
* Discount Analysis
* Caching & Performance Optimization
* Local LLM Integration
* PandasAI
* Ollama
* LiteLLM
* AI-assisted Data Analytics

---

# 👨‍💻 Author

Akshay Mevada

**Data Analyst | Python | Power BI | SQL | Excel | AI Analytics**

---

# ⭐ Support

If you find this project useful for learning **Data Analytics, Streamlit, Power BI, Python, or Local AI**, consider giving the repository a ⭐.

---

# 📄 License

This project is intended for **educational, learning, and portfolio purposes**.

Add an appropriate open-source license to the repository if you intend to distribute the project publicly.
