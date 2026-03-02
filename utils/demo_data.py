"""
utils/demo_data.py
Canned responses used when no AWS credentials are provided (demo mode).
"""

DEMO_RESPONSES = [
    {
        "message": "Great! I'll help you model an E-commerce data warehouse. Before I start designing, I have a few questions to make sure I get the grain and structure right:",
        "state": "clarifying",
        "questions": [
            "What's the reporting grain? (per order, per order line item, or per day?)",
            "Do you have existing customer and product master data, or should I include those as dimensions?",
            "Any specific KPIs you need to track? (revenue, units sold, return rate?)",
            "Should customer history be tracked over time (SCD Type 2), or is the latest snapshot enough?"
        ],
        "model": None
    },
    {
        "message": "Perfect — based on what you've shared I'm designing a **star schema** with FACT_ORDER at the grain of one row per order line item. Here's the model:\n\n✅ FACT_ORDER — core measurements\n✅ DIM_CUSTOMER — SCD Type 2 customer master\n✅ DIM_PRODUCT — product catalog with hierarchy\n✅ DIM_DATE — date dimension (pre-loaded)\n✅ DIM_GEOGRAPHY — location hierarchy from shipping address\n\nI've mapped all source fields to target columns and generated the ER diagram, lineage, DDL, and ETL. Check the tabs on the right!",
        "state": "complete",
        "questions": [],
        "model": {
            "tables": [
                {
                    "name": "FACT_ORDER",
                    "type": "fact",
                    "description": "One row per order line item — grain: order_id + product_id",
                    "columns": [
                        {"name": "order_sk",        "type": "BIGINT",        "pk": True,  "fk": None,                          "description": "Surrogate key"},
                        {"name": "order_id",         "type": "VARCHAR(50)",   "pk": False, "fk": None,                          "description": "Natural key from source"},
                        {"name": "customer_sk",      "type": "BIGINT",        "pk": False, "fk": "DIM_CUSTOMER.customer_sk",    "description": "FK to customer dimension"},
                        {"name": "product_sk",       "type": "BIGINT",        "pk": False, "fk": "DIM_PRODUCT.product_sk",      "description": "FK to product dimension"},
                        {"name": "order_date_sk",    "type": "INTEGER",       "pk": False, "fk": "DIM_DATE.date_sk",            "description": "FK to date dimension"},
                        {"name": "geography_sk",     "type": "INTEGER",       "pk": False, "fk": "DIM_GEOGRAPHY.geography_sk",  "description": "FK to geography dimension"},
                        {"name": "quantity",         "type": "INTEGER",       "pk": False, "fk": None,                          "description": "Units ordered"},
                        {"name": "unit_price",       "type": "DECIMAL(18,2)", "pk": False, "fk": None,                          "description": "Price per unit at time of sale"},
                        {"name": "discount_amount",  "type": "DECIMAL(18,2)", "pk": False, "fk": None,                          "description": "Discount applied"},
                        {"name": "tax_amount",       "type": "DECIMAL(18,2)", "pk": False, "fk": None,                          "description": "Tax charged"},
                        {"name": "shipping_fee",     "type": "DECIMAL(18,2)", "pk": False, "fk": None,                          "description": "Delivery charge"},
                        {"name": "net_revenue",      "type": "DECIMAL(18,2)", "pk": False, "fk": None,                          "description": "(unit_price * quantity) - discount"},
                        {"name": "order_status",     "type": "VARCHAR(20)",   "pk": False, "fk": None,                          "description": "Fulfillment status"},
                        {"name": "payment_method",   "type": "VARCHAR(50)",   "pk": False, "fk": None,                          "description": "Payment type"},
                        {"name": "return_flag",      "type": "BOOLEAN",       "pk": False, "fk": None,                          "description": "Whether item was returned"},
                        {"name": "load_ts",          "type": "TIMESTAMP",     "pk": False, "fk": None,                          "description": "ETL load timestamp"},
                    ]
                },
                {
                    "name": "DIM_CUSTOMER",
                    "type": "dimension",
                    "description": "Customer master — SCD Type 2",
                    "columns": [
                        {"name": "customer_sk",      "type": "BIGINT",        "pk": True,  "fk": None, "description": "Surrogate key"},
                        {"name": "customer_id",      "type": "VARCHAR(50)",   "pk": False, "fk": None, "description": "Natural key"},
                        {"name": "first_name",       "type": "VARCHAR(100)",  "pk": False, "fk": None, "description": "Customer first name"},
                        {"name": "last_name",        "type": "VARCHAR(100)",  "pk": False, "fk": None, "description": "Customer last name"},
                        {"name": "email",            "type": "VARCHAR(255)",  "pk": False, "fk": None, "description": "Email address"},
                        {"name": "customer_segment", "type": "VARCHAR(50)",   "pk": False, "fk": None, "description": "VIP / Regular / New"},
                        {"name": "effective_from",   "type": "DATE",          "pk": False, "fk": None, "description": "SCD2 start date"},
                        {"name": "effective_to",     "type": "DATE",          "pk": False, "fk": None, "description": "SCD2 end date"},
                        {"name": "is_current",       "type": "BOOLEAN",       "pk": False, "fk": None, "description": "Current record flag"},
                    ]
                },
                {
                    "name": "DIM_PRODUCT",
                    "type": "dimension",
                    "description": "Product catalog with category hierarchy",
                    "columns": [
                        {"name": "product_sk",    "type": "BIGINT",        "pk": True,  "fk": None, "description": "Surrogate key"},
                        {"name": "product_id",    "type": "VARCHAR(50)",   "pk": False, "fk": None, "description": "SKU natural key"},
                        {"name": "product_name",  "type": "VARCHAR(255)",  "pk": False, "fk": None, "description": "Product display name"},
                        {"name": "category",      "type": "VARCHAR(100)",  "pk": False, "fk": None, "description": "Product category"},
                        {"name": "subcategory",   "type": "VARCHAR(100)",  "pk": False, "fk": None, "description": "Product subcategory"},
                        {"name": "brand",         "type": "VARCHAR(100)",  "pk": False, "fk": None, "description": "Brand name"},
                        {"name": "unit_cost",     "type": "DECIMAL(18,2)", "pk": False, "fk": None, "description": "Standard cost"},
                    ]
                },
                {
                    "name": "DIM_DATE",
                    "type": "dimension",
                    "description": "Date dimension — preloaded for 10 years",
                    "columns": [
                        {"name": "date_sk",     "type": "INTEGER", "pk": True,  "fk": None, "description": "YYYYMMDD integer key"},
                        {"name": "full_date",   "type": "DATE",    "pk": False, "fk": None, "description": "Calendar date"},
                        {"name": "year",        "type": "INTEGER", "pk": False, "fk": None, "description": "Calendar year"},
                        {"name": "quarter",     "type": "INTEGER", "pk": False, "fk": None, "description": "Quarter 1–4"},
                        {"name": "month",       "type": "INTEGER", "pk": False, "fk": None, "description": "Month 1–12"},
                        {"name": "week",        "type": "INTEGER", "pk": False, "fk": None, "description": "ISO week number"},
                        {"name": "day_of_week", "type": "INTEGER", "pk": False, "fk": None, "description": "0=Monday"},
                        {"name": "is_weekend",  "type": "BOOLEAN", "pk": False, "fk": None, "description": "Weekend flag"},
                    ]
                },
                {
                    "name": "DIM_GEOGRAPHY",
                    "type": "dimension",
                    "description": "Geographic hierarchy from shipping address",
                    "columns": [
                        {"name": "geography_sk", "type": "INTEGER",     "pk": True,  "fk": None, "description": "Surrogate key"},
                        {"name": "zip_code",     "type": "VARCHAR(10)", "pk": False, "fk": None, "description": "Postal code"},
                        {"name": "city",         "type": "VARCHAR(100)","pk": False, "fk": None, "description": "City"},
                        {"name": "state",        "type": "VARCHAR(50)", "pk": False, "fk": None, "description": "State / Province"},
                        {"name": "country",      "type": "VARCHAR(50)", "pk": False, "fk": None, "description": "Country"},
                        {"name": "region",       "type": "VARCHAR(50)", "pk": False, "fk": None, "description": "Sales region"},
                    ]
                },
            ],
            "lineage": [
                {"source_field": "OrderID",              "source_description": "Unique order identifier",      "target_table": "FACT_ORDER",    "target_column": "order_id",        "transformation": "direct",      "logic": "Copy as-is; generate surrogate key via MD5"},
                {"source_field": "CustomerID",           "source_description": "Customer identifier",          "target_table": "DIM_CUSTOMER",  "target_column": "customer_id",     "transformation": "lookup",      "logic": "Lookup / create DIM_CUSTOMER record; return customer_sk to fact"},
                {"source_field": "ProductSKU",           "source_description": "Stock keeping unit",           "target_table": "DIM_PRODUCT",   "target_column": "product_id",      "transformation": "lookup",      "logic": "Lookup DIM_PRODUCT by SKU; return product_sk to fact"},
                {"source_field": "OrderDate",            "source_description": "Date order was placed",        "target_table": "FACT_ORDER",    "target_column": "order_date_sk",   "transformation": "derived",     "logic": "Convert to YYYYMMDD integer for DIM_DATE join"},
                {"source_field": "ShippingZip",          "source_description": "Delivery postal code",         "target_table": "DIM_GEOGRAPHY", "target_column": "zip_code",        "transformation": "lookup",      "logic": "Lookup / enrich geography dim; return geography_sk to fact"},
                {"source_field": "Quantity",             "source_description": "Units ordered",                "target_table": "FACT_ORDER",    "target_column": "quantity",        "transformation": "direct",      "logic": "Cast to INTEGER"},
                {"source_field": "UnitSalePrice",        "source_description": "Price per unit",               "target_table": "FACT_ORDER",    "target_column": "unit_price",      "transformation": "direct",      "logic": "Cast to DECIMAL(18,2)"},
                {"source_field": "DiscountPct",          "source_description": "Discount percentage",          "target_table": "FACT_ORDER",    "target_column": "discount_amount", "transformation": "calculated",  "logic": "UnitSalePrice × Quantity × (DiscountPct / 100)"},
                {"source_field": "TaxAmount",            "source_description": "Tax charged",                  "target_table": "FACT_ORDER",    "target_column": "tax_amount",      "transformation": "direct",      "logic": "Cast to DECIMAL(18,2)"},
                {"source_field": "ShippingFee",          "source_description": "Delivery charge",              "target_table": "FACT_ORDER",    "target_column": "shipping_fee",    "transformation": "direct",      "logic": "Cast to DECIMAL(18,2)"},
                {"source_field": "UnitSalePrice+Qty-Disc","source_description": "Derived revenue",             "target_table": "FACT_ORDER",    "target_column": "net_revenue",     "transformation": "calculated",  "logic": "(UnitSalePrice × Quantity) − discount_amount"},
                {"source_field": "OrderStatus",          "source_description": "Fulfillment status code",      "target_table": "FACT_ORDER",    "target_column": "order_status",    "transformation": "direct",      "logic": "Map code to label: Pending / Shipped / Delivered"},
                {"source_field": "CustomerFirstName",    "source_description": "Customer first name",          "target_table": "DIM_CUSTOMER",  "target_column": "first_name",      "transformation": "direct",      "logic": "Direct copy; SCD2 tracked"},
                {"source_field": "CustomerLastName",     "source_description": "Customer last name",           "target_table": "DIM_CUSTOMER",  "target_column": "last_name",       "transformation": "direct",      "logic": "Direct copy; SCD2 tracked"},
                {"source_field": "CustomerEmail",        "source_description": "Customer email address",       "target_table": "DIM_CUSTOMER",  "target_column": "email",           "transformation": "direct",      "logic": "Lowercase and trim whitespace"},
                {"source_field": "CustomerSegment",      "source_description": "Business classification",      "target_table": "DIM_CUSTOMER",  "target_column": "customer_segment","transformation": "direct",      "logic": "Direct copy; SCD2 tracked"},
                {"source_field": "ProductName",          "source_description": "Product display name",         "target_table": "DIM_PRODUCT",   "target_column": "product_name",    "transformation": "direct",      "logic": "Direct copy"},
                {"source_field": "ProductCategory",      "source_description": "Top-level category",           "target_table": "DIM_PRODUCT",   "target_column": "category",        "transformation": "direct",      "logic": "Direct copy"},
                {"source_field": "ProductSubcategory",   "source_description": "Second-level category",        "target_table": "DIM_PRODUCT",   "target_column": "subcategory",     "transformation": "direct",      "logic": "Direct copy"},
                {"source_field": "BrandName",            "source_description": "Manufacturer brand",           "target_table": "DIM_PRODUCT",   "target_column": "brand",           "transformation": "direct",      "logic": "Direct copy"},
                {"source_field": "UnitCostPrice",        "source_description": "Cost to company",              "target_table": "DIM_PRODUCT",   "target_column": "unit_cost",       "transformation": "direct",      "logic": "Cast to DECIMAL(18,2)"},
                {"source_field": "ReturnFlag",           "source_description": "Whether item returned",        "target_table": "FACT_ORDER",    "target_column": "return_flag",     "transformation": "direct",      "logic": "Cast string 'true'/'false' to BOOLEAN"},
                {"source_field": "PaymentMethod",        "source_description": "How customer paid",            "target_table": "FACT_ORDER",    "target_column": "payment_method",  "transformation": "direct",      "logic": "Direct copy"},
            ],
            "mermaid_er": """erDiagram
    FACT_ORDER {
        BIGINT order_sk PK
        VARCHAR order_id
        BIGINT customer_sk FK
        BIGINT product_sk FK
        INTEGER order_date_sk FK
        INTEGER geography_sk FK
        INTEGER quantity
        DECIMAL unit_price
        DECIMAL discount_amount
        DECIMAL net_revenue
        VARCHAR order_status
        BOOLEAN return_flag
    }
    DIM_CUSTOMER {
        BIGINT customer_sk PK
        VARCHAR customer_id
        VARCHAR first_name
        VARCHAR last_name
        VARCHAR email
        VARCHAR customer_segment
        DATE effective_from
        DATE effective_to
        BOOLEAN is_current
    }
    DIM_PRODUCT {
        BIGINT product_sk PK
        VARCHAR product_id
        VARCHAR product_name
        VARCHAR category
        VARCHAR subcategory
        VARCHAR brand
        DECIMAL unit_cost
    }
    DIM_DATE {
        INTEGER date_sk PK
        DATE full_date
        INTEGER year
        INTEGER quarter
        INTEGER month
        BOOLEAN is_weekend
    }
    DIM_GEOGRAPHY {
        INTEGER geography_sk PK
        VARCHAR zip_code
        VARCHAR city
        VARCHAR state
        VARCHAR country
        VARCHAR region
    }
    FACT_ORDER }o--|| DIM_CUSTOMER : "placed by"
    FACT_ORDER }o--|| DIM_PRODUCT : "contains"
    FACT_ORDER }o--|| DIM_DATE : "ordered on"
    FACT_ORDER }o--|| DIM_GEOGRAPHY : "shipped to"
""",
            "ddl": None,   # will be generated by generators.py
            "etl": None,   # will be generated by generators.py
        }
    },
    {
        "message": "The model looks good! A few things you might want to refine next:\n\n1. **Returns** — should I add a separate FACT_RETURN table, or is the return_flag on FACT_ORDER enough?\n2. **Sales Rep** — your source has SalesRepID. Should I add a DIM_SALES_REP dimension?\n3. **Warehouse** — WarehouseID could be its own dimension if you want to analyze fulfillment by location.\n\nWant me to expand the model with any of these?",
        "state": "complete",
        "questions": [],
        "model": None
    },
]
