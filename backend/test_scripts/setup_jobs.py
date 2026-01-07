from services.sheets import write_to_sheet, ensure_sheet_exists

# Define the Jobs
headers = ["Job Title", "Description", "Required Skills", "Top Projects Reference"]

jobs = [
    [
        "Agentic AI Developer",
        "We are looking for an expert in building autonomous agents using LangGraph, Python, and LLMs. You will design and implement multi-agent workflows, integrate vector databases, and optimize RAG pipelines.",
        "Python, LangGraph, FastAPI, LLMs (OpenAI/Llama), Vector DBs",
        "Built a multi-agent coding assistant, Implemented a complex RAG pipeline, Deployed autonomous agents in production"
    ],
    [
        "Sales and Marketing",
        "We need a dynamic Sales and Marketing lead to drive B2B growth. Responsibilities include lead generation, cold outreach, CRM management, and creating digital marketing campaigns.",
        "Sales Strategy, Digital Marketing, CRM (Salesforce/HubSpot), Communication, SEO",
        "Increased B2B revenue by 30%, Launched a successful product Go-To-Market campaign, Managed a sales team of 5+"
    ]
]

# Ensure Schema
ensure_sheet_exists("ActiveJobSheet")

# Write Headers
write_to_sheet("ActiveJobSheet!A1:D1", [headers])

# Write Jobs (Row 2 and 3)
write_to_sheet("ActiveJobSheet!A2:D3", jobs)

print("✅ ActiveJobSheet populated with: Agentic AI Developer & Sales and Marketing")
