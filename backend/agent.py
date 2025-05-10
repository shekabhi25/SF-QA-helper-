"""
Salesforce AI Chatbot - Agent Implementation
Handles processing queries and generating responses using CrewAI with Google Gemini
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
import re

from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

from tools import SalesforceQueryTool, FieldAccessTool, DataVisualizationTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up Google Gemini API key
GEMINI_API_KEY = "AIzaSyBlpyTc48FxdP7pzsPTK36EVO_Y0QKhkQg"
genai.configure(api_key=GEMINI_API_KEY)

class SalesforceAIAgent:
    """
    AI agent that processes queries from the Salesforce chatbot
    """
    
    def __init__(self):
        """Initialize the agent with language models and tools"""
        self.llm = self._init_language_model()
        self.tools = self._init_tools()
        
        # Create agents
        self._create_agents()
    
    def _init_language_model(self):
        """Initialize the Google Gemini language model"""
        try:
            return ChatGoogleGenerativeAI(
                model="gemini-1.5-flash", 
                google_api_key=GEMINI_API_KEY,
                temperature=0.2,
                convert_system_message_to_human=True
            )
        except Exception as e:
            logger.error(f"Error initializing Gemini language model: {str(e)}")
            raise
    
    def _init_tools(self):
        """Initialize tools for the agents"""
        return {
            "salesforce_query": SalesforceQueryTool(),
            "field_access": FieldAccessTool(),
            "data_visualization": DataVisualizationTool()
        }
    
    def _create_agents(self):
        """Create CrewAI agents"""
        
        # Query analyzer agent
        self.analyzer_agent = Agent(
            role="Query Analyzer",
            goal="Understand user queries about Salesforce data and permissions",
            backstory="""You are an expert at understanding natural language queries about
            Salesforce data and translating them to actionable tasks. You have deep
            knowledge of Salesforce's data model and security model.""",
            verbose=True,
            allow_delegation=True,
            llm=self.llm
        )
        
        # Salesforce data expert agent
        self.data_agent = Agent(
            role="Salesforce Data Expert",
            goal="Retrieve accurate data from Salesforce based on user queries",
            backstory="""You are an expert at writing SOQL queries and retrieving data
            from Salesforce. You understand relationships between objects and can efficiently
            extract the data users need.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.tools["salesforce_query"]],
            llm=self.llm
        )
        
        # Security expert agent
        self.security_agent = Agent(
            role="Salesforce Security Expert",
            goal="Check user permissions and access to Salesforce objects and fields",
            backstory="""You are an expert in Salesforce security, including profiles,
            permission sets, field-level security, and sharing rules. You can determine
            if users have access to specific data.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.tools["field_access"]],
            llm=self.llm
        )
        
        # Visualization expert agent
        self.visualization_agent = Agent(
            role="Data Visualization Expert",
            goal="Create effective visualizations for Salesforce data",
            backstory="""You are an expert in data visualization, particularly with
            Chart.js. You can create clear, informative charts and graphs that help
            users understand their Salesforce data.""",
            verbose=True,
            allow_delegation=False,
            tools=[self.tools["data_visualization"]],
            llm=self.llm
        )
        
        # Response formatter agent
        self.formatter_agent = Agent(
            role="Response Formatter",
            goal="Format AI responses in a clear, concise, and helpful way",
            backstory="""You are an expert at taking complex information and presenting
            it in a format that is easy to understand. You craft responses that are
            professional, accurate, and tailored to the user's question.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def get_available_models(self) -> List[str]:
        """Returns a list of available language models"""
        return ["gemini-1.5-flash"]
    
    def process_query(
        self,
        query_text: str,
        user_id: str,
        username: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a query from the user and generate a response
        
        Args:
            query_text: The user's query text
            user_id: The Salesforce user ID
            username: The Salesforce username
            context: Additional context from Salesforce
            
        Returns:
            Dictionary with response information
        """
        try:
            logger.info(f"Processing query: {query_text}")
            
            # Store user context for tools to access
            if context:
                for tool_name, tool in self.tools.items():
                    if hasattr(tool, "set_user_context"):
                        tool.set_user_context(context)
            
            # Check if this is a field access query
            if self._is_field_access_query(query_text):
                return self._process_field_access_query(query_text, context)
            
            # Check if this is a data visualization query
            elif self._is_visualization_query(query_text):
                return self._process_visualization_query(query_text, context)
            
            # Otherwise process as a general data query
            else:
                return self._process_data_query(query_text, context)
                
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}", exc_info=True)
            return {
                "text": f"I encountered an error processing your query: {str(e)}. Please try a different question or contact your administrator.",
                "error": str(e)
            }
    
    def _is_field_access_query(self, query_text: str) -> bool:
        """Check if this is a query about field access permissions"""
        access_keywords = [
            "access", "permission", "field-level security", "fls",
            "can i see", "can i edit", "can i update", "can i create",
            "visible", "editable", "have access", "have permission"
        ]
        
        # Check if query contains field access keywords
        return any(keyword in query_text.lower() for keyword in access_keywords)
    
    def _is_visualization_query(self, query_text: str) -> bool:
        """Check if this is a query about data visualization"""
        viz_keywords = [
            "chart", "graph", "plot", "visualization", "visualize",
            "dashboard", "report", "show me", "display", "trend",
            "distribution", "comparison", "pie chart", "bar graph",
            "line chart", "histogram"
        ]
        
        # Check if query contains visualization keywords
        return any(keyword in query_text.lower() for keyword in viz_keywords)
    
    def _process_field_access_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a query about field access permissions"""
        # Extract object and field names from the query
        object_name, field_name = self._extract_object_field(query_text)
        
        if not object_name or not field_name:
            # Create a task for the security agent to analyze the query
            task = Task(
                description=f"""
                Analyze this query about field access permissions: "{query_text}"
                Identify the object and field being referenced, then check if the user has access.
                """,
                agent=self.security_agent
            )
            
            # Execute the task
            result = task.execute()
        else:
            # Check field access directly if we extracted object and field
            access_result = self.tools["field_access"].check_field_access(
                object_name=object_name,
                field_name=field_name,
                context=context
            )
            
            result = f"Field Access Check: {access_result}"
        
        # Format the response
        response_task = Task(
            description=f"""
            Format this field access check result into a clear, professional response:
            Query: "{query_text}"
            Result: {result}
            """,
            agent=self.formatter_agent
        )
        
        formatted_response = response_task.execute()
        
        return {
            "text": formatted_response,
            "field_access": True,
            "query_text": query_text
        }
    
    def _process_visualization_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a query about data visualization"""
        # Create a task for the analyzer agent
        analysis_task = Task(
            description=f"""
            Analyze this visualization request: "{query_text}"
            Determine what data needs to be queried and what type of visualization would be most appropriate.
            """,
            agent=self.analyzer_agent
        )
        
        # Execute the task
        analysis_result = analysis_task.execute()
        
        # Create a task for the data agent to retrieve the data
        data_task = Task(
            description=f"""
            Based on this analysis: "{analysis_result}"
            Query the necessary data from Salesforce for visualization.
            """,
            agent=self.data_agent
        )
        
        # Execute the task
        data_result = data_task.execute()
        
        # Create a task for the visualization agent to create the visualization
        viz_task = Task(
            description=f"""
            Create a visualization based on:
            Analysis: "{analysis_result}"
            Data: {data_result}
            """,
            agent=self.visualization_agent
        )
        
        # Execute the task
        viz_result = viz_task.execute()
        
        try:
            viz_data = json.loads(viz_result)
        except:
            # If the result isn't valid JSON, create a basic response
            viz_data = {
                "type": "bar",
                "title": "Data Visualization",
                "data": {
                    "labels": ["Error"],
                    "datasets": [{
                        "label": "Error creating visualization",
                        "data": [0],
                        "backgroundColor": "rgba(255, 99, 132, 0.2)"
                    }]
                }
            }
        
        # Create a task for the formatter agent to create the response text
        response_task = Task(
            description=f"""
            Create a clear explanation for this visualization:
            Query: "{query_text}"
            Analysis: "{analysis_result}"
            Data: {data_result}
            """,
            agent=self.formatter_agent
        )
        
        # Execute the task
        response_text = response_task.execute()
        
        return {
            "text": response_text,
            "visualization": viz_data,
            "query_text": query_text
        }
    
    def _process_data_query(self, query_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a general data query"""
        # Create a task for the analyzer agent
        analysis_task = Task(
            description=f"""
            Analyze this data query: "{query_text}"
            Determine what Salesforce objects and fields are being referenced and what data needs to be retrieved.
            """,
            agent=self.analyzer_agent
        )
        
        # Execute the task
        analysis_result = analysis_task.execute()
        
        # Create a task for the data agent to retrieve the data
        data_task = Task(
            description=f"""
            Based on this analysis: "{analysis_result}"
            Query the necessary data from Salesforce.
            """,
            agent=self.data_agent
        )
        
        # Execute the task
        data_result = data_task.execute()
        
        # Create a task for the formatter agent to create the response
        response_task = Task(
            description=f"""
            Format this data result into a clear, professional response:
            Query: "{query_text}"
            Analysis: "{analysis_result}"
            Data result: {data_result}
            """,
            agent=self.formatter_agent
        )
        
        # Execute the task
        formatted_response = response_task.execute()
        
        return {
            "text": formatted_response,
            "query_text": query_text
        }
    
    def _extract_object_field(self, query_text: str) -> tuple:
        """
        Extract object and field names from a query
        
        Returns:
            Tuple of (object_name, field_name)
        """
        # Look for patterns like "Object.Field" or "Object Field"
        dot_pattern = r'(\w+)\.(\w+)'
        space_pattern = r'(\w+) (?:field|object)'
        
        # Try to match the dot pattern first
        dot_match = re.search(dot_pattern, query_text)
        if dot_match:
            return dot_match.group(1), dot_match.group(2)
        
        # Try to match the space pattern
        space_match = re.search(space_pattern, query_text)
        if space_match:
            # This won't get the field name, but at least we have the object
            return space_match.group(1), None
        
        return None, None 