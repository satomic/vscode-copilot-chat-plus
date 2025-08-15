import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from elasticsearch import Elasticsearch, NotFoundError
from utils.log_utils import logger
import utils.time_utils as time_utils
import time
import json
    


class ElasticsearchManager:

    def __init__(self, url=None, primary_key="id", user=None, password=None, connect_timeout=60, request_timeout=60):

        if url is None:
            url = os.environ.get('ELASTICSEARCH_URL', "http://localhost:9200")

        self.url = url
        self.primary_key = primary_key
        self.user = user
        self.password = password
        self.request_timeout = request_timeout

        try:
            # 尝试创建较新版本的Elasticsearch客户端
            if self.user is None or self.password is None:
                logger.info(f"Using Elasticsearch without authentication (request_timeout={request_timeout}s)")
                self.es = Elasticsearch(
                    hosts=self.url,
                    max_retries=3,
                    retry_on_timeout=True,
                    request_timeout=request_timeout,
                )
            else:
                logger.info(f"Using basic authentication for Elasticsearch (request_timeout={request_timeout}s)")
                self.es = Elasticsearch(
                    hosts=self.url,
                    basic_auth=(self.user, self.password),
                    max_retries=3,
                    retry_on_timeout=True,
                    request_timeout=request_timeout,
                )
        except TypeError:
            # 兼容旧版本的Elasticsearch客户端
            logger.info("Falling back to older Elasticsearch client API")
            if self.user is None or self.password is None:
                logger.info(f"Using Elasticsearch without authentication (request_timeout={request_timeout}s)")
                self.es = Elasticsearch(
                    hosts=self.url,
                    max_retries=3,
                    retry_on_timeout=True,
                    request_timeout=request_timeout,
                )
            else:
                logger.info(f"Using basic authentication for Elasticsearch (request_timeout={request_timeout}s)")
                # 使用http_auth而不是basic_auth，适用于较旧版本
                self.es = Elasticsearch(
                    hosts=self.url,
                    http_auth=(self.user, self.password),
                    max_retries=3,
                    retry_on_timeout=True,
                    request_timeout=request_timeout,
                )


    def check_and_create_indexes(self, indexes={}):

        # try ping with current request timeout
        for i in range(3):  # Reduce retries to 3
            try:
                # 尝试使用参数化的ping方法
                try:
                    ping_result = self.es.ping(request_timeout=self.request_timeout)
                except TypeError:
                    # 如果旧版API不支持request_timeout参数，则使用不带参数的ping
                    ping_result = self.es.ping()
                    
                if ping_result:
                    logger.info("Elasticsearch is up and running")
                    break
                else:
                    logger.warning("Elasticsearch is not responding, retrying...")
                    time.sleep(1)  # Reduce wait time to 1 second
            except Exception as e:
                logger.warning(f"Elasticsearch ping error: {str(e)}, retrying...")
                time.sleep(1)  # Reduce wait time to 1 second

        for index_name, mapping_file in indexes.items():
            if not self.es.indices.exists(index=index_name):
                with open(mapping_file, 'r') as f:
                    mapping = json.load(f)
                self.es.indices.create(index=index_name, body=mapping)
                logger.info(f"created index: {index_name}")
            else:
                logger.info(f"index already exists: {index_name}")

    def write_to_es(self, index_name, data, update_condition=None):
        last_updated_at = time_utils.current_iso8601_time()
        data['last_updated_at'] = last_updated_at
        doc_id = data.get(self.primary_key)
        logger.debug(f"Writing data to Elasticsearch index: {index_name}")
        try:
            # Get existing document
            existing_doc = self.es.get(index=index_name, id=doc_id)

            # Check update condition if provided
            if update_condition:
                should_preserve_fields = True
                for field, value in update_condition.items():
                    if field not in existing_doc['_source'] or existing_doc['_source'][field] != value:
                        should_preserve_fields = False
                        break

                if should_preserve_fields:
                    # Preserve fields listed in update_condition by copying their values from existing document
                    for field in update_condition.keys():
                        if field in existing_doc['_source']:
                            data[field] = existing_doc['_source'][field]
                    logger.info(f'[partial update] to [{index_name}]: {doc_id} - preserving fields: {list(update_condition.keys())}')

            # Always update document, possibly with some preserved fields
            self.es.update(index=index_name, id=doc_id, doc=data)
            logger.debug(f'[updated] to [{index_name}]: {data}')
        except NotFoundError:
            self.es.index(index=index_name, id=doc_id, document=data)
            logger.info(f'[created] to [{index_name}]: {data}') 

    def query_from_es(self, index_name, query, fields=None, sort=None, size=10000):
        """
        Executes a search query on the specified Elasticsearch index and returns the results.

        Args:
            index_name (str): The name of the Elasticsearch index to query.
            query (dict): The Elasticsearch query DSL as a dictionary.
            fields (list, optional): List of fields to include in the response. If None, all fields are returned. Defaults to None.
            size (int, optional): The maximum number of results to return. Defaults to 10000.
            sort (list, optional): List of sort conditions, e.g., [{"created_at": {"order": "desc"}}]. Defaults to None.

        Returns:
            list: A list of dictionaries, each representing a document's source data from the search results.

        Example:
            query = {
                "bool": {
                    "must": [
                        {"match": {"user": "alice"}}
                    ]
                }
            }
            fields = ["user", "timestamp", "action"]
            sort = [{"timestamp": {"order": "desc"}}]
            results = query_from_es("user-actions", query, fields, size=100, sort=sort)
        """
        body = {
            "query": query
        }
        if fields:
            body["_source"] = fields
        if sort:
            body["sort"] = sort
        try:
            results = self.es.search(index=index_name, body=body, size=size)
            hits = results.get('hits', {}).get('hits', [])
            return [hit['_source'] for hit in hits]
        except NotFoundError:
            logger.warning(f"Index '{index_name}' not found.")
            return []
        except Exception as e:
            logger.error(f"Error querying Elasticsearch: {e}")
            return []
    

    def delete_indexes(self, index_names):
        if isinstance(index_names, str):
            index_names = [index_names]
        
        for index_name in index_names:
            try:
                self.es.indices.delete(index=index_name)
                logger.info(f"Index '{index_name}' deleted successfully.")
            except NotFoundError:
                logger.warning(f"Index '{index_name}' not found.")
            except Exception as e:
                logger.error(f"Error deleting index '{index_name}': {e}")
    
    def clear_project_data(self, project_indexes=None):
        """
        Clear all data from project-related indexes without deleting the indexes themselves.
        This preserves the index structure while removing all documents.
        
        Args:
            project_indexes (list, optional): List of index names to clear. 
                                            If None, defaults to all project indexes.
        """
        if project_indexes is None:
            # Default project indexes based on the mapping files
            project_indexes = ["commits", "projects", "mrs", "users"]
        
        if isinstance(project_indexes, str):
            project_indexes = [project_indexes]
        
        cleared_indexes = []
        failed_indexes = []
        
        for index_name in project_indexes:
            try:
                # Check if index exists
                if not self.es.indices.exists(index=index_name):
                    logger.warning(f"Index '{index_name}' does not exist, skipping.")
                    continue
                
                # Delete all documents from the index using delete_by_query
                query = {"match_all": {}}
                
                # Use the appropriate API call based on Elasticsearch version
                try:
                    # Try ES 8.x+ syntax first
                    result = self.es.delete_by_query(
                        index=index_name,
                        query=query,
                        conflicts='proceed',  # Continue if conflicts occur
                        wait_for_completion=True,
                        refresh=True
                    )
                except TypeError:
                    # Fallback to ES 7.x syntax
                    body = {
                        "query": query
                    }
                    result = self.es.delete_by_query(
                        index=index_name,
                        body=body,
                        conflicts='proceed',
                        wait_for_completion=True,
                        refresh=True
                    )
                
                deleted_count = result.get('deleted', 0)
                logger.info(f"Cleared {deleted_count} documents from index '{index_name}'.")
                cleared_indexes.append({"index": index_name, "deleted": deleted_count})
                
            except Exception as e:
                error_msg = f"Error clearing index '{index_name}': {e}"
                logger.error(error_msg)
                failed_indexes.append({"index": index_name, "error": str(e)})
        
        return {
            "cleared": cleared_indexes,
            "failed": failed_indexes,
            "total_cleared": len(cleared_indexes),
            "total_failed": len(failed_indexes)
        }
    
    def count_documents(self, index_name, query):
        """
        Counts the number of documents in the specified Elasticsearch index that match the query.
        
        Args:
            index_name (str): The name of the Elasticsearch index to query.
            query (dict): The Elasticsearch query DSL as a dictionary.
        
        Returns:
            int: The number of documents that match the query.
            
        Example:
            count = count_documents("projects", {"match_all": {}})
        """
        try:
            # Compatibility with both ES 7.x (body param) and 8.x (query param)
            try:
                result = self.es.count(index=index_name, query=query)
            except TypeError:
                # Fallback for older Elasticsearch versions
                body = {"query": query}
                result = self.es.count(index=index_name, body=body)
                
            return result.get('count', 0)
        except NotFoundError:
            logger.warning(f"Index '{index_name}' not found.")
            return 0
        except Exception as e:
            logger.error(f"Error counting documents in Elasticsearch: {e}")
            return 0


if __name__ == "__main__":
    es = ElasticsearchManager(url="http://192.168.50.221:9200")
    # ret = es.query_from_es(
    #     index_name="projects",
    #     query={
    #         "match": {
    #             "id": 135744
    #         }
    #     },
    #     fields=["id", "name", "description"],
    #     size=10
    # )
    
    es.delete_indexes([
        "commits",
        "projects",
        "mrs",
        "users"
    ])
