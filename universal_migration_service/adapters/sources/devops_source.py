"""
Azure DevOps API Source Adapter
"""
import requests
import json
import re
import base64
from typing import Iterator, Dict, List, Any
from datetime import datetime, date, time
from collections.abc import MutableMapping
from urllib.parse import quote
import logging
from .base_source import BaseSourceAdapter

logger = logging.getLogger(__name__)

# Table names
TABLE_MAIN = "DEVOPS_WORKITEMS_MAIN"
TABLE_UPDATES = "DEVOPS_WORKITEMS_UPDATES"
TABLE_COMMENTS = "DEVOPS_WORKITEMS_COMMENTS"
TABLE_RELATIONS = "DEVOPS_WORKITEMS_RELATIONS"
TABLE_REVISIONS = "DEVOPS_WORKITEMS_REVISIONS"
TABLE_PROJECTS = "DEVOPS_PROJECTS"
TABLE_TEAMS = "DEVOPS_TEAMS"

# API version for projects and teams endpoints
PROJECTS_TEAMS_API_VERSION = "7.1-preview.3"


class DevOpsSourceAdapter(BaseSourceAdapter):
    """Azure DevOps API source adapter"""
    
    def __init__(self):
        self.access_token = None
        self.organization = None
        self.api_version = "7.1"
        self.api_base_url = None
        self.config = None
        self._projects_cache = None
        self._teams_cache = None
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to Azure DevOps API"""
        try:
            self.config = config
            self.access_token = config.get('access_token')
            self.organization = config.get('organization')
            self.api_version = config.get('api_version', '7.1')
            
            if not self.access_token or not self.organization:
                raise ConnectionError("access_token and organization are required")
            
            self.api_base_url = f"https://dev.azure.com/{self.organization}"
            
            # Test connection by fetching projects
            headers = self._get_auth_headers()
            test_url = f"{self.api_base_url}/_apis/projects?api-version={self.api_version}"
            resp = requests.get(test_url, headers=headers, timeout=30)
            
            if resp.status_code != 200:
                raise ConnectionError(f"Failed to connect to Azure DevOps: {resp.status_code}")
            
            logger.info(f"Connected to Azure DevOps organization: {self.organization}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Azure DevOps API: {str(e)}")
            raise ConnectionError(f"Failed to connect to Azure DevOps API: {str(e)}")
    
    def disconnect(self):
        """Disconnect from Azure DevOps API"""
        self.access_token = None
        self.organization = None
        self.api_base_url = None
        self._projects_cache = None
        self._teams_cache = None
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """Test Azure DevOps API connection"""
        try:
            access_token = config.get('access_token')
            organization = config.get('organization')
            api_version = config.get('api_version', '7.1')
            
            if not access_token or not organization:
                return False
            
            api_base_url = f"https://dev.azure.com/{organization}"
            headers = self._get_auth_headers_for_token(access_token)
            test_url = f"{api_base_url}/_apis/projects?api-version={api_version}"
            resp = requests.get(test_url, headers=headers, timeout=30)
            return resp.status_code == 200
        except:
            return False
    
    def _get_auth_headers(self):
        """Get authentication headers for Azure DevOps API"""
        return self._get_auth_headers_for_token(self.access_token)
    
    def _get_auth_headers_for_token(self, token: str):
        """Get authentication headers for a specific token"""
        credentials = base64.b64encode(f":{token}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json"
        }
    
    def list_tables(self) -> List[str]:
        """List all available Azure DevOps tables"""
        return [
            TABLE_PROJECTS,
            TABLE_TEAMS,
            TABLE_MAIN,
            TABLE_UPDATES,
            TABLE_COMMENTS,
            TABLE_RELATIONS,
            TABLE_REVISIONS
        ]
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema"""
        if table_name == TABLE_PROJECTS:
            return [
                {"name": "id", "type": "string", "nullable": False},
                {"name": "name", "type": "string", "nullable": True},
                {"name": "description", "type": "string", "nullable": True},
                {"name": "state", "type": "string", "nullable": True},
                {"name": "revision", "type": "int64", "nullable": True},
                {"name": "lastUpdateTime", "type": "string", "nullable": True}
            ]
        elif table_name == TABLE_TEAMS:
            return [
                {"name": "id", "type": "string", "nullable": False},
                {"name": "name", "type": "string", "nullable": True},
                {"name": "description", "type": "string", "nullable": True},
                {"name": "projectName", "type": "string", "nullable": True},
                {"name": "projectId", "type": "string", "nullable": True}
            ]
        elif table_name == TABLE_MAIN:
            # Dynamic schema - return basic structure, will be expanded during data read
            return [
                {"name": "id", "type": "string", "nullable": False}
            ]
        elif table_name == TABLE_UPDATES:
            # Dynamic schema - return basic structure
            return [
                {"name": "work_item_id", "type": "string", "nullable": False},
                {"name": "rev", "type": "int64", "nullable": False}
            ]
        elif table_name == TABLE_REVISIONS:
            # Dynamic schema - return basic structure
            return [
                {"name": "work_item_id", "type": "string", "nullable": False},
                {"name": "rev", "type": "int64", "nullable": False}
            ]
        elif table_name == TABLE_COMMENTS:
            return [
                {"name": "work_item_id", "type": "string", "nullable": False},
                {"name": "comment_id", "type": "string", "nullable": True},
                {"name": "text", "type": "string", "nullable": True},
                {"name": "created_date", "type": "string", "nullable": True},
                {"name": "created_by", "type": "string", "nullable": True},
                {"name": "modified_date", "type": "string", "nullable": True},
                {"name": "modified_by", "type": "string", "nullable": True},
                {"name": "is_deleted", "type": "int64", "nullable": True}
            ]
        elif table_name == TABLE_RELATIONS:
            return [
                {"name": "work_item_id", "type": "string", "nullable": False},
                {"name": "relation_type", "type": "string", "nullable": True},
                {"name": "related_work_item_id", "type": "string", "nullable": True},
                {"name": "related_work_item_url", "type": "string", "nullable": True},
                {"name": "attributes_name", "type": "string", "nullable": True}
            ]
        else:
            return []
    
    def read_data(self, table_name: str, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Read data from Azure DevOps in batches"""
        if not self.access_token:
            raise ConnectionError("Not connected to Azure DevOps API")
        
        if table_name == TABLE_PROJECTS:
            yield from self._read_projects()
        elif table_name == TABLE_TEAMS:
            yield from self._read_teams()
        elif table_name == TABLE_MAIN:
            yield from self._read_work_items_main(batch_size)
        elif table_name == TABLE_UPDATES:
            yield from self._read_work_items_updates(batch_size)
        elif table_name == TABLE_COMMENTS:
            yield from self._read_work_items_comments(batch_size)
        elif table_name == TABLE_RELATIONS:
            yield from self._read_work_items_relations(batch_size)
        elif table_name == TABLE_REVISIONS:
            yield from self._read_work_items_revisions(batch_size)
        else:
            raise ValueError(f"Unknown table: {table_name}")
    
    def read_incremental(self, table_name: str, last_sync_time: datetime, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Read incremental changes (not supported for Azure DevOps - returns all data)"""
        logger.warning(f"Incremental sync for Azure DevOps reads all data (no native incremental support)")
        yield from self.read_data(table_name, batch_size)
    
    def get_source_type(self) -> str:
        return "devops"
    
    # ==================== Helper Methods ====================
    
    def _read_projects(self) -> Iterator[List[Dict[str, Any]]]:
        """Read all projects"""
        if self._projects_cache is None:
            self._projects_cache = self._get_all_projects_full_data()
        
        if self._projects_cache:
            yield self._projects_cache
    
    def _read_teams(self) -> Iterator[List[Dict[str, Any]]]:
        """Read all teams"""
        if self._teams_cache is None:
            self._teams_cache = self._get_all_teams()
        
        if self._teams_cache:
            yield self._teams_cache
    
    def _read_work_items_main(self, batch_size: int) -> Iterator[List[Dict[str, Any]]]:
        """Read work items main data"""
        projects = self._get_all_projects()
        headers = self._get_auth_headers()
        
        for project in projects:
            project_name = project["name"]
            work_item_ids = self._get_all_work_item_ids(headers, project_name)
            
            if not work_item_ids:
                continue
            
            # Process in batches
            for batch_start in range(0, len(work_item_ids), batch_size):
                batch_end = min(batch_start + batch_size, len(work_item_ids))
                batch_ids = work_item_ids[batch_start:batch_end]
                
                work_items = self._fetch_work_items_batch(project_name, batch_ids, headers)
                
                main_records = []
                for work_item in work_items:
                    main_record = self._extract_core_workitem_fields(work_item)
                    if main_record:
                        main_records.append(main_record)
                
                if main_records:
                    yield main_records
    
    def _read_work_items_updates(self, batch_size: int) -> Iterator[List[Dict[str, Any]]]:
        """Read work items updates data"""
        projects = self._get_all_projects()
        headers = self._get_auth_headers()
        
        for project in projects:
            project_name = project["name"]
            work_item_ids = self._get_all_work_item_ids(headers, project_name)
            
            if not work_item_ids:
                continue
            
            # Process in batches
            for batch_start in range(0, len(work_item_ids), batch_size):
                batch_end = min(batch_start + batch_size, len(work_item_ids))
                batch_ids = work_item_ids[batch_start:batch_end]
                
                work_items = self._fetch_work_items_batch(project_name, batch_ids, headers)
                
                all_updates = []
                for work_item in work_items:
                    updates_data = self._get_work_item_updates(work_item, headers)
                    updates = self._extract_updates_data(work_item, updates_data)
                    all_updates.extend(updates)
                
                if all_updates:
                    yield all_updates
    
    def _read_work_items_comments(self, batch_size: int) -> Iterator[List[Dict[str, Any]]]:
        """Read work items comments data"""
        projects = self._get_all_projects()
        headers = self._get_auth_headers()
        
        for project in projects:
            project_name = project["name"]
            work_item_ids = self._get_all_work_item_ids(headers, project_name)
            
            if not work_item_ids:
                continue
            
            # Process in batches
            for batch_start in range(0, len(work_item_ids), batch_size):
                batch_end = min(batch_start + batch_size, len(work_item_ids))
                batch_ids = work_item_ids[batch_start:batch_end]
                
                work_items = self._fetch_work_items_batch(project_name, batch_ids, headers)
                
                all_comments = []
                for work_item in work_items:
                    comments = self._extract_comments_data(work_item, headers)
                    all_comments.extend(comments)
                
                if all_comments:
                    yield all_comments
    
    def _read_work_items_relations(self, batch_size: int) -> Iterator[List[Dict[str, Any]]]:
        """Read work items relations data"""
        projects = self._get_all_projects()
        headers = self._get_auth_headers()
        
        for project in projects:
            project_name = project["name"]
            work_item_ids = self._get_all_work_item_ids(headers, project_name)
            
            if not work_item_ids:
                continue
            
            # Process in batches
            for batch_start in range(0, len(work_item_ids), batch_size):
                batch_end = min(batch_start + batch_size, len(work_item_ids))
                batch_ids = work_item_ids[batch_start:batch_end]
                
                work_items = self._fetch_work_items_batch(project_name, batch_ids, headers)
                
                all_relations = []
                for work_item in work_items:
                    relations = self._extract_relations_data(work_item)
                    all_relations.extend(relations)
                
                if all_relations:
                    yield all_relations
    
    def _read_work_items_revisions(self, batch_size: int) -> Iterator[List[Dict[str, Any]]]:
        """Read work items revisions data"""
        projects = self._get_all_projects()
        headers = self._get_auth_headers()
        
        for project in projects:
            project_name = project["name"]
            work_item_ids = self._get_all_work_item_ids(headers, project_name)
            
            if not work_item_ids:
                continue
            
            # Process in batches
            for batch_start in range(0, len(work_item_ids), batch_size):
                batch_end = min(batch_start + batch_size, len(work_item_ids))
                batch_ids = work_item_ids[batch_start:batch_end]
                
                work_items = self._fetch_work_items_batch(project_name, batch_ids, headers)
                
                all_revisions = []
                for work_item in work_items:
                    revisions_data = self._get_work_item_revisions(project_name, work_item, headers)
                    revisions = self._extract_revisions_data(work_item, revisions_data)
                    all_revisions.extend(revisions)
                
                if all_revisions:
                    yield all_revisions
    
    # ==================== API Methods (from script) ====================
    
    def _get_all_projects(self):
        """Get all projects from the Azure DevOps organization"""
        if self._projects_cache is not None:
            # Return simplified projects list
            return [{"name": p.get("name", ""), "id": p.get("id", "")} for p in self._projects_cache]
        
        logger.info("Discovering all projects in organization...")
        headers = self._get_auth_headers()
        projects_url = f"{self.api_base_url}/_apis/projects?api-version={self.api_version}"
        
        all_projects = []
        skip = 0
        top = 100
        
        while True:
            url = f"{projects_url}&$skip={skip}&$top={top}"
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    logger.error(f"Failed to fetch projects: {resp.status_code}")
                    break
                
                result = resp.json()
                projects = result.get("value", [])
                
                if not projects:
                    break
                
                for project in projects:
                    project_name = project.get("name", "")
                    project_state = project.get("state", "")
                    if project_state.lower() == "wellformed" and project_name:
                        all_projects.append({
                            "name": project_name,
                            "id": project.get("id", "")
                        })
                
                if len(projects) < top:
                    break
                
                skip += top
                
            except Exception as e:
                logger.error(f"Error fetching projects: {e}")
                break
        
        logger.info(f"Found {len(all_projects)} project(s)")
        return all_projects
    
    def _get_all_projects_full_data(self):
        """Fetch ALL projects with full data for DEVOPS_PROJECTS table"""
        logger.info("Fetching all projects with full data from Azure DevOps...")
        headers = self._get_auth_headers()
        projects_url = f"{self.api_base_url}/_apis/projects?api-version={PROJECTS_TEAMS_API_VERSION}"
        
        all_projects = []
        skip = 0
        top = 100
        
        while True:
            url = f"{projects_url}&$skip={skip}&$top={top}"
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    logger.warning(f"Failed to fetch projects (skip={skip}): {resp.status_code}")
                    break
                
                result = resp.json()
                projects = result.get("value", [])
                
                if not projects:
                    break
                
                for project in projects:
                    project_id = project.get("id", "")
                    project_name = project.get("name", "")
                    description = project.get("description", "")
                    state = project.get("state", "")
                    revision = project.get("revision", 0)
                    last_update_time = project.get("lastUpdateTime", "")
                    
                    project_record = {
                        "id": project_id,
                        "name": project_name,
                        "description": description,
                        "state": state,
                        "revision": revision,
                        "lastUpdateTime": last_update_time
                    }
                    all_projects.append(project_record)
                
                if len(projects) < top:
                    break
                
                skip += top
                
            except Exception as e:
                logger.warning(f"Error fetching projects: {e}")
                break
        
        logger.info(f"Total projects fetched: {len(all_projects)}")
        return all_projects
    
    def _get_all_teams(self):
        """Fetch ALL teams from Azure DevOps API"""
        logger.info("Fetching all teams from Azure DevOps...")
        headers = self._get_auth_headers()
        teams_url = f"{self.api_base_url}/_apis/teams?api-version={PROJECTS_TEAMS_API_VERSION}"
        
        all_teams = []
        skip = 0
        top = 100
        
        while True:
            url = f"{teams_url}&$skip={skip}&$top={top}"
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    logger.warning(f"Failed to fetch teams (skip={skip}): {resp.status_code}")
                    break
                
                result = resp.json()
                teams = result.get("value", [])
                
                if not teams:
                    break
                
                for team in teams:
                    team_id = team.get("id", "")
                    team_name = team.get("name", "")
                    description = team.get("description", "")
                    project_name = team.get("projectName", "")
                    project_id = team.get("projectId", "")
                    
                    team_record = {
                        "id": team_id,
                        "name": team_name,
                        "description": description,
                        "projectName": project_name,
                        "projectId": project_id
                    }
                    all_teams.append(team_record)
                
                if len(teams) < top:
                    break
                
                skip += top
                
            except Exception as e:
                logger.warning(f"Error fetching teams: {e}")
                break
        
        logger.info(f"Total teams fetched: {len(all_teams)}")
        return all_teams
    
    def _get_all_work_item_ids(self, headers, project_name):
        """Get all work item IDs from a project using WIQL"""
        project_name_encoded = quote(project_name, safe='')
        wiql_query = {
            "query": f"SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '{project_name}' ORDER BY [System.Id]"
        }
        
        wiql_url = f"{self.api_base_url}/{project_name_encoded}/_apis/wit/wiql?api-version={self.api_version}"
        
        try:
            resp = requests.post(wiql_url, json=wiql_query, headers=headers, timeout=60)
            if resp.status_code != 200:
                logger.warning(f"Failed WIQL query for {project_name}: {resp.status_code}")
                return []
            
            wiql_result = resp.json()
            work_item_refs = wiql_result.get("workItems", [])
            
            work_item_ids = [str(ref.get("id", "")) for ref in work_item_refs if ref.get("id")]
            return work_item_ids
        except Exception as e:
            logger.warning(f"Error fetching work item IDs for {project_name}: {e}")
            return []
    
    def _fetch_work_items_batch(self, project_name, work_item_ids, headers):
        """Fetch work items in batch"""
        if not work_item_ids:
            return []
        
        project_name_encoded = quote(project_name, safe='')
        ids_str = ",".join(work_item_ids)
        workitems_url = f"{self.api_base_url}/{project_name_encoded}/_apis/wit/workitems?ids={ids_str}&$expand=all&api-version={self.api_version}"
        
        try:
            resp = requests.get(workitems_url, headers=headers, timeout=120)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch work items batch: {resp.status_code}")
                return []
            
            batch_result = resp.json()
            work_items = batch_result.get("value", [])
            return work_items
        except Exception as e:
            logger.warning(f"Error fetching work items batch: {e}")
            return []
    
    def _get_work_item_updates(self, work_item, headers):
        """Get updates for a work item"""
        updates_url = work_item.get("_links", {}).get("workItemUpdates", {}).get("href", "")
        if not updates_url:
            return None
        
        try:
            updates_resp = requests.get(updates_url, headers=headers, timeout=30)
            if updates_resp.status_code == 200:
                return updates_resp.json().get("value", [])
        except:
            pass
        return None
    
    def _get_work_item_revisions(self, project_name, work_item, headers):
        """Get revisions for a work item"""
        work_item_id = str(work_item.get("id", ""))
        project_name_encoded = quote(project_name, safe='')
        revisions_url = f"{self.api_base_url}/{project_name_encoded}/_apis/wit/workitems/{work_item_id}/revisions?api-version={self.api_version}"
        
        try:
            revisions_resp = requests.get(revisions_url, headers=headers, timeout=30)
            if revisions_resp.status_code == 200:
                return revisions_resp.json().get("value", [])
        except:
            pass
        return None
    
    # ==================== Data Extraction Methods (from script) ====================
    
    def _extract_core_workitem_fields(self, work_item):
        """Extract core fields from work item - only columns that exist in ClickHouse MAIN table"""
        fields = work_item.get("fields", {})
        
        def get_field_value(*possible_names):
            for name in possible_names:
                if name in fields:
                    val = fields.get(name)
                    if val == 0:
                        return 0
                    return val if val else ""
            return ""
        
        def get_user_display_name(user_obj):
            if isinstance(user_obj, dict):
                return user_obj.get("displayName", "")
            return ""
        
        def get_user_unique_name(user_obj):
            if isinstance(user_obj, dict):
                return user_obj.get("uniqueName", "")
            return ""
        
        core_fields = {
            "id": str(work_item.get("id", "")),
            "AreaPath": fields.get("System.AreaPath", ""),
            "TeamProject": fields.get("System.TeamProject", ""),
            "IterationPath": fields.get("System.IterationPath", ""),
            "WorkItemType": fields.get("System.WorkItemType", ""),
            "State": fields.get("System.State", ""),
            "Reason": fields.get("System.Reason", ""),
            "AssignedTo": get_user_display_name(fields.get("System.AssignedTo", {})),
            "CreatedDate": fields.get("System.CreatedDate", ""),
            "CreatedBy_uniqueName": get_user_unique_name(fields.get("System.CreatedBy", {})),
            "ChangedDate": fields.get("System.ChangedDate", ""),
            "ChangedBy_uniqueName": get_user_unique_name(fields.get("System.ChangedBy", {})),
            "CommentCount": fields.get("System.CommentCount", 0) if fields.get("System.CommentCount") is not None else 0,
            "Title": fields.get("System.Title", ""),
            "StateChangeDate": get_field_value("Microsoft.VSTS.Common.StateChangeDate", "System.StateChangeDate", "Custom.StateChangeDate"),
            "ActivatedDate": get_field_value("Microsoft.VSTS.Common.ActivatedDate", "System.ActivatedDate", "Custom.ActivatedDate"),
            "ActivatedBy_displayName": get_user_display_name(fields.get("Microsoft.VSTS.Common.ActivatedBy", {})),
            "ResolvedDate": get_field_value("Microsoft.VSTS.Common.ResolvedDate", "System.ResolvedDate", "Custom.ResolvedDate"),
            "ResolvedBy_displayName": get_user_display_name(fields.get("Microsoft.VSTS.Common.ResolvedBy", {})),
            "ClosedDate": get_field_value("Microsoft.VSTS.Common.ClosedDate", "System.ClosedDate", "Custom.ClosedDate"),
            "ClosedBy_displayName": get_user_display_name(fields.get("Microsoft.VSTS.Common.ClosedBy", {})),
            "Priority": fields.get("Microsoft.VSTS.Common.Priority", ""),
            "ValueArea": fields.get("Microsoft.VSTS.Common.ValueArea", ""),
            "TargetDate": get_field_value("Microsoft.VSTS.Scheduling.TargetDate", "Custom.TargetDate", "TargetDate"),
            "Effort": fields.get("Microsoft.VSTS.Scheduling.Effort", ""),
            "StartDate": get_field_value("Microsoft.VSTS.Scheduling.StartDate", "Custom.StartDate", "StartDate"),
            "Product": get_field_value("Custom.Product", "Custom.product", "Product", "product"),
            "ScrumTeam": get_field_value("Custom.scrumTeam", "Custom.ScrumTeam", "Custom.scrum_team", "scrumTeam"),
            "Device": get_field_value("Custom.device", "Custom.Device", "device"),
            "Category": get_field_value("System.Category", "Custom.category", "Custom.Category", "category"),
            "Urgent": get_field_value("Custom.urgent", "Custom.Urgent", "urgent"),
            "TotalEfforts": get_field_value("Custom.totalEfforts", "Custom.TotalEfforts", "Custom.total_efforts", "Microsoft.VSTS.Scheduling.OriginalEstimate", "totalEfforts"),
            "ActualEfforts": get_field_value("Custom.ActualEfforts", "Custom.actualEfforts", "Custom.actual_efforts", "Microsoft.VSTS.Scheduling.CompletedWork", "ActualEfforts"),
            "SprintEfforts": get_field_value("Custom.SprintEfforts", "Custom.sprintEfforts", "Custom.sprint_efforts", "SprintEfforts"),
            "StoppageReworkCount": get_field_value("Custom.StoppageReworkCount", "Custom.stoppageReworkCount", "StoppageReworkCount"),
            "RemainingEfforts": get_field_value("Custom.RemainingEfforts", "Custom.remainingEfforts", "Custom.remaining_efforts", "Microsoft.VSTS.Scheduling.RemainingWork", "RemainingEfforts"),
            "WeekEfforts": get_field_value("Custom.WeekEfforts", "Custom.weekEfforts", "WeekEfforts"),
            "CustomerName": get_field_value("Custom.customer", "Custom.Customer", "customer", "CustomerName"),
            "description": str(fields.get("System.Description", ""))[:1000],
        }
        return core_fields
    
    def _extract_updates_data(self, work_item, updates_data):
        """Extract updates/history data - flatten API and accumulate state across updates"""
        updates = []
        work_item_id = str(work_item.get("id", ""))
        
        # Track current state across updates
        current_state = {
            "revisedBy_displayName": None,
            "revisedBy_uniqueName": None,
            "revisedDate": None,
            "AuthorizedDate": None,
            "WorkItemType": None,
            "State": None,
            "Reason": None,
            "CreatedDate": None,
            "CreatedBy_displayName": None,
            "CreatedBy_uniqueName": None,
            "ChangedDate": None,
            "ChangedBy_displayName": None,
            "ChangedBy_uniqueName": None,
            "AuthorizedAs_displayName": None,
            "AuthorizedAs_uniqueName": None,
            "CommentCount": None,
            "TeamProject": None,
            "AreaPath": None,
            "IterationPath": None,
            "Priority": None,
            "StartDate": None,
            "Product": None,
            "ScrumTeam": None,
            "Device": None,
            "Category": None,
            "Effort": None,
            "TargetDate": None,
            "StateChangeDate": None,
            "Title": None,
        }
        
        def get_update_user_display_name(user_obj):
            if isinstance(user_obj, dict):
                return user_obj.get("displayName", "")
            return ""
        
        def get_update_user_unique_name(user_obj):
            if isinstance(user_obj, dict):
                return user_obj.get("uniqueName", "")
            return ""
        
        def get_field_value(fields_dict, field_name, state_key=None):
            field_obj = fields_dict.get(field_name, {})
            if isinstance(field_obj, dict):
                if "newValue" in field_obj:
                    val = field_obj.get("newValue")
                    if state_key:
                        current_state[state_key] = val
                    return val
            if state_key:
                return current_state.get(state_key)
            return None
        
        def get_user_field(fields_dict, field_name, attr_name, state_key_display=None, state_key_unique=None):
            field_obj = fields_dict.get(field_name, {})
            if isinstance(field_obj, dict):
                new_val = field_obj.get("newValue", {})
                if isinstance(new_val, dict):
                    display_val = new_val.get("displayName", "")
                    unique_val = new_val.get("uniqueName", "")
                    if state_key_display:
                        current_state[state_key_display] = display_val
                    if state_key_unique:
                        current_state[state_key_unique] = unique_val
                    if attr_name == "displayName":
                        return display_val
                    elif attr_name == "uniqueName":
                        return unique_val
            if attr_name == "displayName" and state_key_display:
                return current_state.get(state_key_display)
            elif attr_name == "uniqueName" and state_key_unique:
                return current_state.get(state_key_unique)
            return None
        
        if updates_data and isinstance(updates_data, list) and len(updates_data) > 0:
            for update in updates_data:
                if not isinstance(update, dict):
                    continue
                
                fields_dict = update.get("fields", {})
                rev = update.get("rev", 0)
                
                revised_by = update.get("revisedBy", {})
                changed_by = update.get("changedBy", {})
                created_by = update.get("createdBy", {})
                authorized_as = update.get("authorizedAs", {})
                
                revised_by_display = get_update_user_display_name(revised_by)
                revised_by_unique = get_update_user_unique_name(revised_by)
                if revised_by_display:
                    current_state["revisedBy_displayName"] = revised_by_display
                if revised_by_unique:
                    current_state["revisedBy_uniqueName"] = revised_by_unique
                
                revised_date = update.get("revisedDate", "")
                if revised_date:
                    current_state["revisedDate"] = revised_date
                
                authorized_date = get_field_value(fields_dict, "System.AuthorizedDate", "AuthorizedDate")
                work_item_type = get_field_value(fields_dict, "System.WorkItemType", "WorkItemType")
                state = get_field_value(fields_dict, "System.State", "State")
                reason = get_field_value(fields_dict, "System.Reason", "Reason")
                created_date = get_field_value(fields_dict, "System.CreatedDate", "CreatedDate")
                changed_date = get_field_value(fields_dict, "System.ChangedDate", "ChangedDate")
                comment_count = get_field_value(fields_dict, "System.CommentCount", "CommentCount")
                team_project = get_field_value(fields_dict, "System.TeamProject", "TeamProject")
                area_path = get_field_value(fields_dict, "System.AreaPath", "AreaPath")
                iteration_path = get_field_value(fields_dict, "System.IterationPath", "IterationPath")
                priority = get_field_value(fields_dict, "Microsoft.VSTS.Common.Priority", "Priority")
                start_date = get_field_value(fields_dict, "Microsoft.VSTS.Scheduling.StartDate", "StartDate")
                product = get_field_value(fields_dict, "Custom.Product", "Product")
                scrum_team = get_field_value(fields_dict, "Custom.ScrumTeam", "ScrumTeam")
                device = get_field_value(fields_dict, "Custom.Device", "Device")
                category = get_field_value(fields_dict, "Custom.Category", "Category")
                effort = get_field_value(fields_dict, "Microsoft.VSTS.Scheduling.Effort", "Effort")
                target_date = get_field_value(fields_dict, "Microsoft.VSTS.Scheduling.TargetDate", "TargetDate")
                state_change_date = get_field_value(fields_dict, "Microsoft.VSTS.Common.StateChangeDate", "StateChangeDate")
                title = get_field_value(fields_dict, "System.Title", "Title")
                
                created_by_display = get_update_user_display_name(created_by) or get_user_field(fields_dict, "System.CreatedBy", "displayName", "CreatedBy_displayName", "CreatedBy_uniqueName")
                created_by_unique = get_update_user_unique_name(created_by) or get_user_field(fields_dict, "System.CreatedBy", "uniqueName", "CreatedBy_displayName", "CreatedBy_uniqueName")
                changed_by_display = get_update_user_display_name(changed_by) or get_user_field(fields_dict, "System.ChangedBy", "displayName", "ChangedBy_displayName", "ChangedBy_uniqueName")
                changed_by_unique = get_update_user_unique_name(changed_by) or get_user_field(fields_dict, "System.ChangedBy", "uniqueName", "ChangedBy_displayName", "ChangedBy_uniqueName")
                authorized_as_display = get_update_user_display_name(authorized_as) or get_user_field(fields_dict, "System.AuthorizedAs", "displayName", "AuthorizedAs_displayName", "AuthorizedAs_uniqueName")
                authorized_as_unique = get_update_user_unique_name(authorized_as) or get_user_field(fields_dict, "System.AuthorizedAs", "uniqueName", "AuthorizedAs_displayName", "AuthorizedAs_uniqueName")
                
                if created_by_display is not None:
                    current_state["CreatedBy_displayName"] = created_by_display
                if created_by_unique is not None:
                    current_state["CreatedBy_uniqueName"] = created_by_unique
                if changed_by_display is not None:
                    current_state["ChangedBy_displayName"] = changed_by_display
                if changed_by_unique is not None:
                    current_state["ChangedBy_uniqueName"] = changed_by_unique
                if authorized_as_display is not None:
                    current_state["AuthorizedAs_displayName"] = authorized_as_display
                if authorized_as_unique is not None:
                    current_state["AuthorizedAs_uniqueName"] = authorized_as_unique
                
                update_record = {
                    "work_item_id": work_item_id,
                    "rev": rev,
                    "revisedBy_displayName": revised_by_display if revised_by_display else current_state.get("revisedBy_displayName"),
                    "revisedBy_uniqueName": revised_by_unique if revised_by_unique else current_state.get("revisedBy_uniqueName"),
                    "revisedDate": revised_date if revised_date else current_state.get("revisedDate"),
                    "AuthorizedDate": authorized_date if authorized_date is not None else current_state.get("AuthorizedDate"),
                    "WorkItemType": work_item_type if work_item_type is not None else current_state.get("WorkItemType"),
                    "State": state if state is not None else current_state.get("State"),
                    "Reason": reason if reason is not None else current_state.get("Reason"),
                    "CreatedDate": created_date if created_date is not None else current_state.get("CreatedDate"),
                    "CreatedBy_displayName": created_by_display if created_by_display is not None else current_state.get("CreatedBy_displayName"),
                    "CreatedBy_uniqueName": created_by_unique if created_by_unique is not None else current_state.get("CreatedBy_uniqueName"),
                    "ChangedDate": changed_date if changed_date is not None else current_state.get("ChangedDate"),
                    "ChangedBy_displayName": changed_by_display if changed_by_display is not None else current_state.get("ChangedBy_displayName"),
                    "ChangedBy_uniqueName": changed_by_unique if changed_by_unique is not None else current_state.get("ChangedBy_uniqueName"),
                    "AuthorizedAs_displayName": authorized_as_display if authorized_as_display is not None else current_state.get("AuthorizedAs_displayName"),
                    "AuthorizedAs_uniqueName": authorized_as_unique if authorized_as_unique is not None else current_state.get("AuthorizedAs_uniqueName"),
                    "CommentCount": comment_count if comment_count is not None else current_state.get("CommentCount"),
                    "TeamProject": team_project if team_project is not None else current_state.get("TeamProject"),
                    "AreaPath": area_path if area_path is not None else current_state.get("AreaPath"),
                    "IterationPath": iteration_path if iteration_path is not None else current_state.get("IterationPath"),
                    "Priority": priority if priority is not None else current_state.get("Priority"),
                    "StartDate": start_date if start_date is not None else current_state.get("StartDate"),
                    "Product": product if product is not None else current_state.get("Product"),
                    "ScrumTeam": scrum_team if scrum_team is not None else current_state.get("ScrumTeam"),
                    "Device": device if device is not None else current_state.get("Device"),
                    "Category": category if category is not None else current_state.get("Category"),
                    "Effort": effort if effort is not None else current_state.get("Effort"),
                    "TargetDate": target_date if target_date is not None else current_state.get("TargetDate"),
                    "StateChangeDate": state_change_date if state_change_date is not None else current_state.get("StateChangeDate"),
                    "Title": title if title is not None else current_state.get("Title"),
                }
                updates.append(update_record)
        else:
            update_record = {
                "work_item_id": work_item_id,
                "rev": None,
                "revisedBy_displayName": None,
                "revisedBy_uniqueName": None,
                "revisedDate": None,
                "AuthorizedDate": None,
                "WorkItemType": None,
                "State": None,
                "Reason": None,
                "CreatedDate": None,
                "CreatedBy_displayName": None,
                "CreatedBy_uniqueName": None,
                "ChangedDate": None,
                "ChangedBy_displayName": None,
                "ChangedBy_uniqueName": None,
                "AuthorizedAs_displayName": None,
                "AuthorizedAs_uniqueName": None,
                "CommentCount": None,
                "TeamProject": None,
                "AreaPath": None,
                "IterationPath": None,
                "Priority": None,
                "StartDate": None,
                "Product": None,
                "ScrumTeam": None,
                "Device": None,
                "Category": None,
                "Effort": None,
                "TargetDate": None,
                "StateChangeDate": None,
                "Title": None,
            }
            updates.append(update_record)
        
        return updates
    
    def _extract_comments_data(self, work_item, headers):
        """Extract comments data - get ALL comments"""
        comments = []
        comments_data = None
        work_item_id = str(work_item.get("id", ""))
        
        links = work_item.get("_links", {})
        comments_link = links.get("workItemComments", {})
        if isinstance(comments_link, dict):
            comments_url = comments_link.get("href")
            if comments_url:
                try:
                    resp = requests.get(comments_url, headers=headers, timeout=30)
                    if resp.status_code == 200:
                        comments_response = resp.json()
                        comments_data = comments_response.get("comments", []) or comments_response.get("value", [])
                except:
                    pass
        
        if comments_data and isinstance(comments_data, list) and len(comments_data) > 0:
            for comment in comments_data:
                if isinstance(comment, dict):
                    comment_record = {
                        "work_item_id": work_item_id,
                        "comment_id": comment.get("id", ""),
                        "text": str(comment.get("text", ""))[:2000],
                        "created_date": comment.get("createdDate", ""),
                        "created_by": comment.get("createdBy", {}).get("displayName", "") if isinstance(comment.get("createdBy"), dict) else "",
                        "modified_date": comment.get("modifiedDate", ""),
                        "modified_by": comment.get("modifiedBy", {}).get("displayName", "") if isinstance(comment.get("modifiedBy"), dict) else "",
                        "is_deleted": 1 if comment.get("isDeleted", False) else 0,
                    }
                    comments.append(comment_record)
        
        if not comments:
            comment_record = {
                "work_item_id": work_item_id,
                "comment_id": None,
                "text": None,
                "created_date": None,
                "created_by": None,
                "modified_date": None,
                "modified_by": None,
                "is_deleted": None,
            }
            comments.append(comment_record)
        
        return comments
    
    def _extract_relations_data(self, work_item):
        """Extract relations data - get ALL relations"""
        relations = []
        relations_list = work_item.get("relations", [])
        work_item_id = str(work_item.get("id", ""))
        
        if relations_list and isinstance(relations_list, list) and len(relations_list) > 0:
            for relation in relations_list:
                if isinstance(relation, dict):
                    relation_record = {
                        "work_item_id": work_item_id,
                        "relation_type": relation.get("rel", ""),
                        "related_work_item_id": relation.get("url", "").split("/")[-1] if relation.get("url") else "",
                        "related_work_item_url": relation.get("url", ""),
                        "attributes_name": relation.get("attributes", {}).get("name", "") if isinstance(relation.get("attributes"), dict) else "",
                    }
                    relations.append(relation_record)
        
        if not relations:
            relation_record = {
                "work_item_id": work_item_id,
                "relation_type": None,
                "related_work_item_id": None,
                "related_work_item_url": None,
                "attributes_name": None,
            }
            relations.append(relation_record)
        
        return relations
    
    def _extract_revisions_data(self, work_item, revisions_data):
        """Extract revisions data - populate all revisions with specific columns from REVISIONS API"""
        revisions = []
        work_item_id = str(work_item.get("id", ""))
        
        def get_field_value(fields_dict, field_name):
            if field_name in fields_dict:
                val = fields_dict.get(field_name)
                if val == 0:
                    return 0
                return val if val else ""
            return ""
        
        def get_user_display_name(user_obj):
            if isinstance(user_obj, dict):
                return user_obj.get("displayName", "")
            return ""
        
        def get_user_unique_name(user_obj):
            if isinstance(user_obj, dict):
                return user_obj.get("uniqueName", "")
            return ""
        
        if revisions_data and isinstance(revisions_data, list) and len(revisions_data) > 0:
            for revision in revisions_data:
                if not isinstance(revision, dict):
                    continue
                
                rev = revision.get("rev", 0)
                fields_dict = revision.get("fields", {})
                
                changed_by_obj = fields_dict.get("System.ChangedBy", {})
                created_by_obj = fields_dict.get("System.CreatedBy", {})
                
                comment_count = fields_dict.get("System.CommentCount")
                if comment_count is not None:
                    comment_count = comment_count if comment_count != 0 else 0
                else:
                    comment_count = ""
                
                revision_record = {
                    "work_item_id": work_item_id,
                    "rev": rev,
                    "WorkItemType": get_field_value(fields_dict, "System.WorkItemType"),
                    "State": get_field_value(fields_dict, "System.State"),
                    "Reason": get_field_value(fields_dict, "System.Reason"),
                    "CreatedDate": get_field_value(fields_dict, "System.CreatedDate"),
                    "CreatedBy_displayName": get_user_display_name(created_by_obj),
                    "CreatedBy_uniqueName": get_user_unique_name(created_by_obj),
                    "ChangedDate": get_field_value(fields_dict, "System.ChangedDate"),
                    "ChangedBy_displayName": get_user_display_name(changed_by_obj),
                    "ChangedBy_uniqueName": get_user_unique_name(changed_by_obj),
                    "CommentCount": comment_count,
                    "TeamProject": get_field_value(fields_dict, "System.TeamProject"),
                    "AreaPath": get_field_value(fields_dict, "System.AreaPath"),
                    "IterationPath": get_field_value(fields_dict, "System.IterationPath"),
                    "Priority": get_field_value(fields_dict, "Microsoft.VSTS.Common.Priority"),
                    "ValueArea": get_field_value(fields_dict, "Microsoft.VSTS.Common.ValueArea"),
                    "StartDate": get_field_value(fields_dict, "Microsoft.VSTS.Scheduling.StartDate"),
                    "Product": get_field_value(fields_dict, "Custom.Product"),
                    "ScrumTeam": get_field_value(fields_dict, "Custom.ScrumTeam"),
                    "Device": get_field_value(fields_dict, "Custom.Device"),
                    "Category": get_field_value(fields_dict, "Custom.Category"),
                    "Effort": get_field_value(fields_dict, "Microsoft.VSTS.Scheduling.Effort"),
                    "TargetDate": get_field_value(fields_dict, "Microsoft.VSTS.Scheduling.TargetDate"),
                    "StateChangeDate": get_field_value(fields_dict, "Microsoft.VSTS.Common.StateChangeDate"),
                    "Title": get_field_value(fields_dict, "System.Title"),
                }
                revisions.append(revision_record)
        else:
            revision_record = {
                "work_item_id": work_item_id,
                "rev": None,
                "WorkItemType": None,
                "State": None,
                "Reason": None,
                "CreatedDate": None,
                "CreatedBy_displayName": None,
                "CreatedBy_uniqueName": None,
                "ChangedDate": None,
                "ChangedBy_displayName": None,
                "ChangedBy_uniqueName": None,
                "CommentCount": None,
                "TeamProject": None,
                "AreaPath": None,
                "IterationPath": None,
                "Priority": None,
                "ValueArea": None,
                "StartDate": None,
                "Product": None,
                "ScrumTeam": None,
                "Device": None,
                "Category": None,
                "Effort": None,
                "TargetDate": None,
                "StateChangeDate": None,
                "Title": None,
            }
            revisions.append(revision_record)
        
        return revisions

