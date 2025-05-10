"""
Salesforce AI Chatbot - Tools for CrewAI Agents
Custom tools that agents can use to process queries
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
from crewai.tools import BaseTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SalesforceQueryTool(BaseTool):
    """Tool for querying Salesforce data"""
    
    name: str = "salesforce_query_tool"
    description: str = "Generates and simulates execution of SOQL queries for Salesforce data retrieval"
    user_context: Optional[Dict[str, Any]] = None
    
    def __init__(self):
        super().__init__()
    
    def set_user_context(self, context: Dict[str, Any]):
        """Set the user context for the tool"""
        self.user_context = context
    
    def _run(self, query_description: str) -> str:
        """
        Processes a query description and returns results
        
        Args:
            query_description: Description of the query to execute
            
        Returns:
            String containing the simulated query results
        """
        logger.info(f"Running Salesforce query: {query_description}")
        
        try:
            # Get the SOQL query from the description
            soql_query = self._extract_soql_query(query_description)
            
            if not soql_query:
                # If no SOQL was found, generate a mock query based on the description
                soql_query = self._generate_mock_soql(query_description)
            
            # Parse the query to understand what objects and fields are being requested
            object_name, fields = self._parse_soql_query(soql_query)
            
            # Check if the user has permission to access these objects/fields
            if self.user_context and object_name:
                self._check_object_access(object_name)
            
            # Generate mock data as a response
            result = self._generate_mock_data(object_name, fields, query_description)
            
            return json.dumps({
                "soql": soql_query,
                "object": object_name,
                "fields": fields,
                "data": result
            })
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return json.dumps({
                "error": f"Error processing query: {str(e)}",
                "query_description": query_description
            })
    
    def _extract_soql_query(self, text: str) -> Optional[str]:
        """
        Extract SOQL query from text if it exists
        
        Args:
            text: Text that might contain a SOQL query
            
        Returns:
            SOQL query string or None if not found
        """
        # Look for patterns that might indicate a SOQL query
        soql_patterns = [
            r'SELECT\s+[\w\.\,\s\(\)]+\s+FROM\s+[\w\.\s]+(\s+WHERE\s+[\w\.\=\s\'\"\<\>\!\+\-\*\/\:\^\&\|\%\$\#\@\,\(\)]+)?(\s+ORDER BY\s+[\w\.\s\,]+)?(\s+LIMIT\s+\d+)?',
            r'SELECT.*FROM.*'
        ]
        
        for pattern in soql_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _generate_mock_soql(self, description: str) -> str:
        """
        Generate a mock SOQL query based on a description
        
        Args:
            description: Description of the query
            
        Returns:
            A SOQL query string
        """
        # Simple heuristics to determine query type
        description_lower = description.lower()
        
        # Check if the query is about accounts
        if "account" in description_lower:
            if "contact" in description_lower:
                return "SELECT Id, Name, (SELECT Id, FirstName, LastName FROM Contacts) FROM Account"
            return "SELECT Id, Name, Industry, Type FROM Account"
        
        # Check if the query is about contacts
        elif "contact" in description_lower:
            return "SELECT Id, FirstName, LastName, Email, Phone FROM Contact"
        
        # Check if the query is about opportunities
        elif "opportunit" in description_lower:
            return "SELECT Id, Name, Amount, CloseDate, StageName FROM Opportunity"
        
        # Default to a basic query
        return "SELECT Id, Name FROM Account LIMIT 10"
    
    def _parse_soql_query(self, soql_query: str) -> tuple:
        """
        Parse a SOQL query to extract object name and fields
        
        Args:
            soql_query: SOQL query string
            
        Returns:
            Tuple of (object_name, fields_list)
        """
        try:
            # Extract object name
            from_match = re.search(r'FROM\s+(\w+)', soql_query, re.IGNORECASE)
            if not from_match:
                return None, []
            
            object_name = from_match.group(1)
            
            # Extract fields
            fields_match = re.search(r'SELECT\s+([\w\.\,\s\(\)]+)\s+FROM', soql_query, re.IGNORECASE)
            if not fields_match:
                return object_name, []
            
            fields_str = fields_match.group(1)
            
            # Handle subqueries by temporarily removing them
            subqueries = []
            
            def replace_subquery(match):
                subqueries.append(match.group(0))
                return f"SUBQUERY_{len(subqueries) - 1}"
            
            # Replace subqueries with placeholders
            fields_str = re.sub(r'\([^)]*\)', replace_subquery, fields_str)
            
            # Split fields by comma
            fields = [f.strip() for f in fields_str.split(',')]
            
            return object_name, fields
            
        except Exception as e:
            logger.error(f"Error parsing SOQL query: {str(e)}")
            return None, []
    
    def _check_object_access(self, object_name: str) -> bool:
        """
        Check if the user has access to the specified object
        
        Args:
            object_name: Name of the Salesforce object
            
        Returns:
            Boolean indicating whether the user has access
        """
        if not self.user_context:
            return True
        
        try:
            object_permissions = self.user_context.get("objectPermissions", {})
            obj_perms = object_permissions.get(object_name, {})
            
            return obj_perms.get("isAccessible", True)
            
        except Exception as e:
            logger.error(f"Error checking object access: {str(e)}")
            return True
    
    def _generate_mock_data(self, object_name: str, fields: List[str], description: str) -> List[Dict[str, Any]]:
        """
        Generate mock data based on object and fields
        
        Args:
            object_name: Name of the Salesforce object
            fields: List of field names
            description: Original query description
            
        Returns:
            List of mock data records
        """
        # Generate a number of records based on the query description
        num_records = 5
        if "count" in description.lower() or "how many" in description.lower():
            num_records = 10
        
        # Generate mock data based on object type
        if object_name and object_name.lower() == "account":
            return self._generate_mock_accounts(num_records, fields)
        elif object_name and object_name.lower() == "contact":
            return self._generate_mock_contacts(num_records, fields)
        elif object_name and object_name.lower() == "opportunity":
            return self._generate_mock_opportunities(num_records, fields)
        
        # Default mock data
        return [{"Id": f"record_{i}", "Name": f"Record {i}"} for i in range(num_records)]
    
    def _generate_mock_accounts(self, num_records: int, fields: List[str]) -> List[Dict[str, Any]]:
        """Generate mock account records"""
        industries = ["Technology", "Finance", "Healthcare", "Manufacturing", "Retail"]
        types = ["Customer", "Partner", "Prospect", "Other"]
        
        accounts = []
        for i in range(num_records):
            account = {
                "Id": f"001{i:09d}",
                "Name": f"Sample Account {i}",
                "Industry": industries[i % len(industries)],
                "Type": types[i % len(types)],
                "AnnualRevenue": i * 100000,
                "NumberOfEmployees": i * 10 + 5
            }
            accounts.append(account)
        
        return accounts
    
    def _generate_mock_contacts(self, num_records: int, fields: List[str]) -> List[Dict[str, Any]]:
        """Generate mock contact records"""
        first_names = ["John", "Jane", "Alex", "Emma", "Michael"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones"]
        
        contacts = []
        for i in range(num_records):
            first_name = first_names[i % len(first_names)]
            last_name = last_names[i % len(last_names)]
            
            contact = {
                "Id": f"003{i:09d}",
                "FirstName": first_name,
                "LastName": last_name,
                "Email": f"{first_name.lower()}.{last_name.lower()}@example.com",
                "Phone": f"(555) 555-{i:04d}",
                "AccountId": f"001{(i % 3):09d}"
            }
            contacts.append(contact)
        
        return contacts
    
    def _generate_mock_opportunities(self, num_records: int, fields: List[str]) -> List[Dict[str, Any]]:
        """Generate mock opportunity records"""
        stages = ["Prospecting", "Qualification", "Needs Analysis", "Closed Won", "Closed Lost"]
        
        opportunities = []
        for i in range(num_records):
            stage = stages[i % len(stages)]
            closed = "Closed" in stage
            
            opportunity = {
                "Id": f"006{i:09d}",
                "Name": f"Sample Opportunity {i}",
                "Amount": (i + 1) * 10000,
                "CloseDate": f"2025-{(i % 12) + 1:02d}-15",
                "StageName": stage,
                "IsClosed": closed,
                "IsWon": stage == "Closed Won",
                "AccountId": f"001{(i % 5):09d}"
            }
            opportunities.append(opportunity)
        
        return opportunities


class FieldAccessTool(BaseTool):
    """Tool for checking field-level access in Salesforce"""
    
    name: str = "field_access_tool"
    description: str = "Checks if a user has access to specific Salesforce fields"
    user_context: Optional[Dict[str, Any]] = None
    
    def __init__(self):
        super().__init__()
    
    def set_user_context(self, context: Dict[str, Any]):
        """Set the user context for the tool"""
        self.user_context = context
    
    def _run(self, query: str) -> str:
        """
        Checks field access for a given query
        
        Args:
            query: Query about field access
            
        Returns:
            String describing field access
        """
        logger.info(f"Checking field access: {query}")
        
        try:
            # Extract object and field from the query
            object_name, field_name = self._extract_object_field(query)
            
            if not object_name or not field_name:
                return json.dumps({
                    "error": "Couldn't identify object and field in the query",
                    "query": query
                })
            
            # Check field access using the user context
            access_info = self.check_field_access(object_name, field_name)
            
            return json.dumps(access_info)
            
        except Exception as e:
            logger.error(f"Error checking field access: {str(e)}")
            return json.dumps({
                "error": f"Error checking field access: {str(e)}",
                "query": query
            })
    
    def check_field_access(self, object_name: str, field_name: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Check if the user has access to a specific field
        
        Args:
            object_name: Name of the Salesforce object
            field_name: Name of the field
            context: User context (optional, will use self.user_context if not provided)
            
        Returns:
            Dictionary with access information
        """
        if context:
            user_context = context
        else:
            user_context = self.user_context
        
        if not user_context:
            return {
                "hasAccess": True,
                "message": "No user context provided, assuming access is granted",
                "object": object_name,
                "field": field_name
            }
        
        try:
            # Get field permissions from the user context
            field_permissions = user_context.get("fieldPermissions", {})
            obj_fields = field_permissions.get(object_name, {})
            
            # Normalize field name (remove namespace prefixes, etc.)
            normalized_field = field_name.split(".")[-1]
            
            # Check for the field in the object's field permissions
            field_perms = obj_fields.get(normalized_field, None)
            
            if field_perms is None:
                # If field not found, use the profile name to make a mock decision
                profile = user_context.get("profile", "Standard User")
                
                # Mock response based on profile
                if profile in ["System Administrator", "Custom Admin"]:
                    hasAccess = True
                    message = f"The user's profile ({profile}) has access to all fields."
                else:
                    # For Sales Rep and other profiles, return more restricted access
                    hasAccess = False
                    restricted_fields = [
                        "Rating", "AnnualRevenue", "Ownership", 
                        "Salary__c", "Internal_Notes__c", "Confidential__c"
                    ]
                    hasAccess = normalized_field not in restricted_fields
                    
                    if hasAccess:
                        message = f"The field {object_name}.{normalized_field} is accessible to the current user's profile {profile}."
                    else:
                        message = f"The field {object_name}.{normalized_field} is not visible to the current user's profile {profile}."
            else:
                # Use actual field permissions
                hasAccess = field_perms.get("isAccessible", False)
                
                if hasAccess:
                    message = f"The field {object_name}.{normalized_field} is accessible to the current user."
                else:
                    message = f"The field {object_name}.{normalized_field} is not accessible to the current user."
            
            return {
                "hasAccess": hasAccess,
                "message": message,
                "object": object_name,
                "field": normalized_field,
                "isUpdateable": field_perms.get("isUpdateable", False) if field_perms else False,
                "isCreateable": field_perms.get("isCreateable", False) if field_perms else False
            }
            
        except Exception as e:
            logger.error(f"Error checking field access: {str(e)}")
            return {
                "hasAccess": False,
                "error": str(e),
                "message": f"Error checking access for {object_name}.{field_name}: {str(e)}",
                "object": object_name,
                "field": field_name
            }
    
    def _extract_object_field(self, query: str) -> tuple:
        """
        Extract object and field from a query
        
        Args:
            query: Query text
            
        Returns:
            Tuple of (object_name, field_name)
        """
        # Look for patterns like "Object.Field" or mentions of fields/objects
        dot_pattern = r'(\w+)\.(\w+)'
        field_pattern = r'field [\'\"]?(\w+)[\'\"]? (?:of|in|on) [\'\"]?(\w+)[\'\"]?'
        access_pattern = r'access to [\'\"]?(\w+)\.(\w+)[\'\"]?'
        
        # Try to match the dot pattern (Object.Field)
        dot_match = re.search(dot_pattern, query)
        if dot_match:
            return dot_match.group(1), dot_match.group(2)
        
        # Try to match field pattern (field X of Object)
        field_match = re.search(field_pattern, query, re.IGNORECASE)
        if field_match:
            return field_match.group(2), field_match.group(1)
        
        # Try to match access pattern (access to Object.Field)
        access_match = re.search(access_pattern, query, re.IGNORECASE)
        if access_match:
            return access_match.group(1), access_match.group(2)
        
        return None, None


class DataVisualizationTool(BaseTool):
    """Tool for creating data visualizations from Salesforce data"""
    
    name: str = "data_visualization_tool"
    description: str = "Creates chart.js visualizations from Salesforce data for display in the chat interface"
    user_context: Optional[Dict[str, Any]] = None
    
    def __init__(self):
        super().__init__()
    
    def set_user_context(self, context: Dict[str, Any]):
        """Set the user context for the tool"""
        self.user_context = context
    
    def _run(self, visualization_request: str) -> str:
        """
        Creates a visualization from a request
        
        Args:
            visualization_request: Description of the visualization to create
            
        Returns:
            JSON string containing visualization data for Chart.js
        """
        logger.info(f"Creating visualization: {visualization_request}")
        
        try:
            # Parse the visualization request
            viz_type, data_description = self._parse_visualization_request(visualization_request)
            
            # Create the visualization data
            visualization = self._create_visualization(viz_type, data_description)
            
            return json.dumps(visualization)
            
        except Exception as e:
            logger.error(f"Error creating visualization: {str(e)}")
            return json.dumps({
                "error": f"Error creating visualization: {str(e)}",
                "type": "bar",
                "title": "Error",
                "data": {
                    "labels": ["Error"],
                    "datasets": [{
                        "label": "Error creating visualization",
                        "data": [0],
                        "backgroundColor": "rgba(255, 99, 132, 0.2)"
                    }]
                }
            })
    
    def _parse_visualization_request(self, request: str) -> tuple:
        """
        Parse a visualization request to determine type and data needs
        
        Args:
            request: Visualization request string
            
        Returns:
            Tuple of (visualization_type, data_description)
        """
        request_lower = request.lower()
        
        # Determine visualization type based on keywords
        viz_type = "bar"  # Default
        
        if "pie" in request_lower or "distribution" in request_lower:
            viz_type = "pie"
        elif "line" in request_lower or "trend" in request_lower or "over time" in request_lower:
            viz_type = "line"
        elif "scatter" in request_lower or "correlation" in request_lower:
            viz_type = "scatter"
        elif "area" in request_lower:
            viz_type = "area"
        
        # Extract data description
        data_description = request
        
        return viz_type, data_description
    
    def _create_visualization(self, viz_type: str, data_description: str) -> Dict[str, Any]:
        """
        Create a visualization based on type and data description
        
        Args:
            viz_type: Type of visualization (bar, pie, line, etc.)
            data_description: Description of the data to visualize
            
        Returns:
            Dictionary with visualization data for Chart.js
        """
        # For debugging, log what we're creating
        logger.info(f"Creating {viz_type} chart based on: {data_description}")
        
        # Determine what data to mock based on the description
        data = self._generate_mock_data(data_description)
        
        # Create base visualization object
        visualization = {
            "type": viz_type,
            "title": self._generate_title(viz_type, data_description),
            "data": {}
        }
        
        # Create the data section based on viz_type
        if viz_type == "pie":
            visualization["data"] = {
                "labels": data["labels"],
                "datasets": [{
                    "data": data["values"],
                    "backgroundColor": self._generate_colors(len(data["labels"])),
                    "borderWidth": 1
                }]
            }
        elif viz_type == "line":
            visualization["data"] = {
                "labels": data["labels"],
                "datasets": [{
                    "label": data.get("dataset_label", "Data"),
                    "data": data["values"],
                    "fill": False,
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "tension": 0.1
                }]
            }
        elif viz_type == "scatter":
            # Generate x, y pairs for scatter plot
            points = []
            for i in range(len(data["values"])):
                points.append({
                    "x": i,
                    "y": data["values"][i]
                })
            
            visualization["data"] = {
                "datasets": [{
                    "label": data.get("dataset_label", "Data"),
                    "data": points,
                    "backgroundColor": "rgba(75, 192, 192, 0.5)"
                }]
            }
        else:  # Default to bar chart
            visualization["data"] = {
                "labels": data["labels"],
                "datasets": [{
                    "label": data.get("dataset_label", "Data"),
                    "data": data["values"],
                    "backgroundColor": self._generate_colors(len(data["labels"])),
                    "borderWidth": 1
                }]
            }
        
        # Add options
        visualization["options"] = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "title": {
                    "display": True,
                    "text": visualization["title"]
                }
            }
        }
        
        return visualization
    
    def _generate_mock_data(self, description: str) -> Dict[str, Any]:
        """
        Generate mock data based on the description
        
        Args:
            description: Description of the data to generate
            
        Returns:
            Dictionary with labels, values, and other data properties
        """
        description_lower = description.lower()
        
        # Account-related visualizations
        if "account" in description_lower and "industry" in description_lower:
            return {
                "labels": ["Technology", "Finance", "Healthcare", "Manufacturing", "Retail"],
                "values": [35, 20, 15, 10, 20],
                "dataset_label": "Accounts by Industry"
            }
        elif "account" in description_lower and "type" in description_lower:
            return {
                "labels": ["Customer", "Partner", "Prospect", "Other"],
                "values": [45, 15, 30, 10],
                "dataset_label": "Accounts by Type"
            }
        
        # Opportunity-related visualizations
        elif "opportunity" in description_lower and "stage" in description_lower:
            return {
                "labels": ["Prospecting", "Qualification", "Needs Analysis", "Closed Won", "Closed Lost"],
                "values": [10, 25, 15, 40, 10],
                "dataset_label": "Opportunities by Stage"
            }
        elif "opportunity" in description_lower and ("amount" in description_lower or "revenue" in description_lower):
            return {
                "labels": ["Q1", "Q2", "Q3", "Q4"],
                "values": [150000, 225000, 300000, 375000],
                "dataset_label": "Opportunity Amount by Quarter"
            }
        
        # Lead-related visualizations
        elif "lead" in description_lower and "source" in description_lower:
            return {
                "labels": ["Web", "Trade Show", "Partner Referral", "Employee Referral", "Other"],
                "values": [30, 15, 25, 20, 10],
                "dataset_label": "Leads by Source"
            }
        
        # Case-related visualizations
        elif "case" in description_lower and "priority" in description_lower:
            return {
                "labels": ["High", "Medium", "Low"],
                "values": [15, 45, 40],
                "dataset_label": "Cases by Priority"
            }
        elif "case" in description_lower and "status" in description_lower:
            return {
                "labels": ["New", "Working", "Escalated", "Closed"],
                "values": [20, 30, 10, 40],
                "dataset_label": "Cases by Status"
            }
        
        # Contact-related visualizations
        elif "contact" in description_lower and "account" in description_lower:
            return {
                "labels": ["Acme Corp", "Universal Containers", "Salesforce", "Microsoft", "IBM"],
                "values": [8, 5, 12, 7, 9],
                "dataset_label": "Contacts by Account"
            }
        
        # Default data if nothing matches
        return {
            "labels": ["Category A", "Category B", "Category C", "Category D", "Category E"],
            "values": [12, 19, 3, 5, 2],
            "dataset_label": "Sample Data"
        }
    
    def _generate_title(self, viz_type: str, description: str) -> str:
        """
        Generate a title for the visualization
        
        Args:
            viz_type: Type of visualization
            description: Description of the data
            
        Returns:
            Title string
        """
        description_lower = description.lower()
        
        # Extract key terms
        object_terms = ["account", "contact", "opportunity", "lead", "case"]
        object_term = next((term for term in object_terms if term in description_lower), "Data")
        
        # Capitalize the object term
        object_term = object_term.capitalize()
        
        # Look for metric terms
        if "by industry" in description_lower:
            return f"{object_term}s by Industry"
        elif "by type" in description_lower:
            return f"{object_term}s by Type"
        elif "by stage" in description_lower:
            return f"{object_term}s by Stage"
        elif "by amount" in description_lower or "by revenue" in description_lower:
            return f"{object_term} Revenue"
        elif "by quarter" in description_lower:
            return f"{object_term}s by Quarter"
        elif "by year" in description_lower:
            return f"{object_term}s by Year"
        elif "by source" in description_lower:
            return f"{object_term}s by Source"
        elif "by priority" in description_lower:
            return f"{object_term}s by Priority"
        elif "by status" in description_lower:
            return f"{object_term}s by Status"
        
        # If no specific pattern matched, generate a generic title
        return f"{object_term} Visualization"
    
    def _generate_colors(self, count: int) -> List[str]:
        """
        Generate a list of colors for the visualization
        
        Args:
            count: Number of colors to generate
            
        Returns:
            List of color strings in rgba format
        """
        base_colors = [
            "rgba(255, 99, 132, 0.6)",    # Red
            "rgba(54, 162, 235, 0.6)",    # Blue
            "rgba(255, 206, 86, 0.6)",    # Yellow
            "rgba(75, 192, 192, 0.6)",    # Green
            "rgba(153, 102, 255, 0.6)",   # Purple
            "rgba(255, 159, 64, 0.6)",    # Orange
            "rgba(199, 199, 199, 0.6)",   # Gray
            "rgba(83, 102, 255, 0.6)",    # Indigo
            "rgba(78, 205, 196, 0.6)",    # Teal
            "rgba(255, 99, 255, 0.6)"     # Pink
        ]
        
        # If we need more colors than in our base set, repeat them
        colors = []
        for i in range(count):
            colors.append(base_colors[i % len(base_colors)])
        
        return colors 
