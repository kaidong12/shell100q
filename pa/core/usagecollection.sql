\CONNECT cqdb primea

DROP SCHEMA IF EXISTS usage_schema CASCADE;
CREATE SCHEMA usage_schema AUTHORIZATION primea;

GRANT ALL ON SCHEMA usage_schema TO primea;
SET search_path=usage_schema;

--Create language plpgsql safely
CREATE OR REPLACE FUNCTION create_language_plpgsql()
RETURNS BOOLEAN AS $$
    CREATE LANGUAGE plpgsql;
    SELECT TRUE;
$$ LANGUAGE SQL;

SELECT CASE WHEN NOT
(
	SELECT  TRUE AS exists
	FROM    pg_language
	WHERE   lanname = 'plpgsql'
	UNION
	SELECT  FALSE AS exists
	ORDER BY exists DESC
	LIMIT 1
)
THEN
    create_language_plpgsql()
ELSE
    FALSE
END AS plpgsql_created;

DROP FUNCTION create_language_plpgsql();


--This is the raw usage stats of handlers per minute
CREATE TABLE handler_stats_per_min (
	start_time timestamp with time zone,
	end_time timestamp with time zone,
	project_name varchar(500),
	component_id varchar(500),
	component_name varchar(50),
	data_count bigint,
	data_volume bigint
);
--This is the raw usage stats of consumers per minute
CREATE TABLE consumer_stats_per_min(
    start_time timestamp with time zone,
	end_time timestamp with time zone,
	project_name varchar(500),
	component_id varchar(500),
	query_id varchar(500),
	component_name varchar(50),
	data_count bigint
);
---This is the summary usage stats of handlers per day
CREATE TABLE handler_stats_per_day (
    hid serial unique not null,
	start_time timestamp with time zone,
	end_time timestamp with time zone,
	project_name varchar(500), 
	component_id varchar(500), 
	component_name varchar(50) , 
	data_count bigint,
	data_volume bigint
);
---This is the summary usage stats of consumers per day
CREATE TABLE consumer_stats_per_day (
	cid serial unique not null,
    start_time timestamp with time zone,
	end_time timestamp with time zone,
	project_name varchar(500), 
	component_id varchar(500),
	query_id varchar(500),
	component_name varchar(50),
	data_count bigint
);
ALTER SEQUENCE handler_stats_per_day_hid_seq START WITH 1 INCREMENT BY 1;
ALTER SEQUENCE consumer_stats_per_day_cid_seq START WITH 1 INCREMENT BY 1;

------------------functions---------------------
-- =============================================
-- Author:        <juanli>
-- Create date:   <2014-01-23>
-- Description:   <summary stats per day and vacuum stats 7 days ago>
-- =============================================
CREATE OR REPLACE FUNCTION sum_vaccum_stats_func(stime timestamp with time zone,etime timestamp with time zone,pname varchar(500))
RETURNS BOOLEAN AS $$
DECLARE cleartime timestamp with time zone;
BEGIN
	---do sum process---
	INSERT INTO usage_schema.handler_stats_per_day(start_time,end_time,project_name,component_id,component_name,data_count,data_volume) 
	SELECT $1,$2,$3,component_id,component_name,SUM(data_count),SUM(data_volume)
	FROM usage_schema.handler_stats_per_min  
	WHERE start_time >= $1 AND start_time < $2 AND project_name = $3 GROUP BY component_id,component_name;
	
	INSERT INTO usage_schema.consumer_stats_per_day(start_time,end_time,project_name,component_id,query_id,component_name,data_count) 
	SELECT $1,$2,$3,component_id,query_id,component_name,SUM(data_count)
	FROM usage_schema.consumer_stats_per_min 
	WHERE start_time >= $1 AND start_time < $2 AND project_name = $3 GROUP BY component_id,query_id,component_name;
	
	---do vaccum process---
	cleartime := $2 + '-7 day';
	DELETE FROM usage_schema.handler_stats_per_min
	WHERE end_time < cleartime AND project_name = $3;
	
	DELETE FROM usage_schema.consumer_stats_per_min
	WHERE  end_time < cleartime AND project_name = $3;
	
	RETURN TRUE;
END;

$$  LANGUAGE plpgsql
    RETURNS NULL ON NULL INPUT
    SECURITY DEFINER
;
-- =============================================
-- Author:        <juanli>
-- Create date:   <2014-01-23>
-- Description:   <summary stats per day and vacuum stats when a project rebooted>
-- =============================================
CREATE OR REPLACE FUNCTION reboot_sum_vaccum_stats_func(stime timestamp with time zone,etime timestamp with time zone,pname varchar(500))
RETURNS BOOLEAN AS $$
DECLARE maxtime timestamp with time zone;
DECLARE cleartime timestamp with time zone;
BEGIN
	cleartime := $2 + '-7 day';
	
	-------process about handler-------
	SELECT MAX(start_time) FROM usage_schema.handler_stats_per_day WHERE project_name = $3 INTO maxtime;
	IF (maxtime IS NULL OR date_trunc('day',maxtime) < date_trunc('day',$1)) THEN
		---do history data aggregation of handler stats---
		INSERT INTO usage_schema.handler_stats_per_day(start_time,end_time,project_name,component_id,component_name,data_count,data_volume) 
		SELECT date_trunc('day',MIN(start_time)),date_trunc('day',MAX(start_time) + '1 day'),$3,component_id,component_name,SUM(data_count),SUM(data_volume)
		FROM usage_schema.handler_stats_per_min  
		WHERE (date_trunc('day',start_time) <= date_trunc('day',$1)) AND project_name = $3 GROUP BY date_trunc('day',start_time),date_trunc('day',end_time),component_id,component_name 
		ORDER BY date_trunc('day',start_time),component_id;
	
		---if the latest history date is still before the current day , 
		---we need to create a row with zero data_volume just as a mark that all the history data has been aggregated.
		SELECT MAX(start_time) FROM usage_schema.handler_stats_per_day WHERE project_name = $3 INTO maxtime;
		IF (maxtime IS NOT NULL AND date_trunc('day',maxtime) < date_trunc('day',$1)) THEN
			INSERT INTO usage_schema.handler_stats_per_day(start_time,end_time,project_name,component_id,component_name,data_count,data_volume) 
			VALUES($1, $1 + '1 day',$3,'-','-',0,0);	
		END IF;
		
		---do history data vacuum---	
		DELETE FROM usage_schema.handler_stats_per_min
		WHERE  end_time < cleartime AND project_name = $3;
	END IF;
	
    --------process about consumer-------
	SELECT MAX(start_time) FROM usage_schema.consumer_stats_per_day WHERE project_name = $3 INTO maxtime;
	IF (maxtime IS NULL OR date_trunc('day',maxtime) < date_trunc('day',$1)) THEN
		---do history data aggregation of handler stats---
		INSERT INTO usage_schema.consumer_stats_per_day(start_time,end_time,project_name,component_id,query_id,component_name,data_count) 
		SELECT date_trunc('day',MIN(start_time)),date_trunc('day',MAX(start_time) + '1 day'),$3,component_id,query_id,component_name,SUM(data_count)
		FROM usage_schema.consumer_stats_per_min  
		WHERE (date_trunc('day',start_time) <= date_trunc('day',$1)) AND project_name = $3 GROUP BY date_trunc('day',start_time),date_trunc('day',end_time),component_id,query_id,component_name 
		ORDER BY date_trunc('day',start_time),component_id;
	
		---if the latest history date is still before the current day , 
		---we need to create a row with zero data_volume just as a mark that all the history data has been aggregated.
		SELECT MAX(start_time) FROM usage_schema.consumer_stats_per_day WHERE project_name = $3 INTO maxtime;
		IF (maxtime IS NOT NULL AND date_trunc('day',maxtime) < date_trunc('day',$1)) THEN
			INSERT INTO usage_schema.consumer_stats_per_day(start_time,end_time,project_name,component_id,query_id,component_name,data_count) 
			VALUES($1, $1 + '1 day',$3,'-','-','-',0);	
		END IF;
			
		---do history data vacuum---	
		DELETE FROM usage_schema.consumer_stats_per_min
		WHERE  end_time < cleartime AND project_name = $3;
	END IF;
	RETURN TRUE;
END;

$$  LANGUAGE plpgsql
    RETURNS NULL ON NULL INPUT
    SECURITY DEFINER
;