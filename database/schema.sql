--
-- PostgreSQL database dump
--

-- Dumped from database version 15.12
-- Dumped by pg_dump version 15.12

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS '';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: asset_source; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.asset_source AS ENUM (
    'system',
    'upload',
    'ai_generated'
);


--
-- Name: asset_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.asset_status AS ENUM (
    'pending',
    'processing',
    'ready',
    'failed'
);


--
-- Name: asset_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.asset_type AS ENUM (
    'avatar',
    'voice',
    'script',
    'storyboard'
);


--
-- Name: emotion_style; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.emotion_style AS ENUM (
    'happy',
    'professional',
    'gentle',
    'excited',
    'serious'
);


--
-- Name: oauth_provider; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.oauth_provider AS ENUM (
    'github',
    'google',
    'wechat'
);


--
-- Name: project_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.project_status AS ENUM (
    'pending',
    'generating_audio',
    'generating_video',
    'post_processing',
    'completed',
    'failed'
);


--
-- Name: user_tier; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_tier AS ENUM (
    'free',
    'pro',
    'enterprise'
);


--
-- Name: video_resolution; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.video_resolution AS ENUM (
    '480p',
    '720p',
    '1080p'
);


--
-- Name: deduct_user_usage(uuid, numeric, bigint, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.deduct_user_usage(p_user_id uuid, p_minutes numeric DEFAULT 0, p_storage_bytes bigint DEFAULT 0, p_videos integer DEFAULT 0) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_current_usage RECORD;
BEGIN
    -- 获取或创建当前计费周期的用量记录
    INSERT INTO user_usage (user_id, billing_cycle_start, billing_cycle_end, minutes_limit, storage_limit_bytes)
    SELECT 
        p_user_id,
        date_trunc('month', CURRENT_DATE)::DATE,
        (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month')::DATE,
        sp.minutes_per_month,
        sp.storage_mb * 1024 * 1024
    FROM users u
    JOIN subscription_plans sp ON u.tier = sp.tier
    WHERE u.id = p_user_id
    ON CONFLICT (user_id, billing_cycle_start) DO NOTHING;
    
    -- 更新用量
    UPDATE user_usage 
    SET 
        minutes_used = minutes_used + p_minutes,
        storage_used_bytes = storage_used_bytes + p_storage_bytes,
        videos_generated = videos_generated + p_videos,
        updated_at = CURRENT_TIMESTAMP
    WHERE user_id = p_user_id
        AND billing_cycle_start <= CURRENT_DATE 
        AND billing_cycle_end > CURRENT_DATE;
    
    RETURN FOUND;
END;
$$;


--
-- Name: get_user_usage(uuid); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_user_usage(p_user_id uuid) RETURNS TABLE(minutes_used numeric, minutes_limit numeric, minutes_remaining numeric, storage_used_bytes bigint, storage_limit_bytes bigint, storage_remaining_bytes bigint, videos_generated integer)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(uu.minutes_used, 0)::DECIMAL,
        COALESCE(uu.minutes_limit, sp.minutes_per_month)::DECIMAL,
        GREATEST(0, COALESCE(uu.minutes_limit, sp.minutes_per_month) - COALESCE(uu.minutes_used, 0))::DECIMAL,
        COALESCE(uu.storage_used_bytes, 0)::BIGINT,
        COALESCE(uu.storage_limit_bytes, sp.storage_mb * 1024 * 1024)::BIGINT,
        GREATEST(0, COALESCE(uu.storage_limit_bytes, sp.storage_mb * 1024 * 1024) - COALESCE(uu.storage_used_bytes, 0))::BIGINT,
        COALESCE(uu.videos_generated, 0)::INTEGER
    FROM users u
    JOIN subscription_plans sp ON u.tier = sp.tier
    LEFT JOIN user_usage uu ON u.id = uu.user_id 
        AND uu.billing_cycle_start <= CURRENT_DATE 
        AND uu.billing_cycle_end > CURRENT_DATE
    WHERE u.id = p_user_id;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: asset_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asset_tags (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    asset_id uuid NOT NULL,
    tag character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: assets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.assets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    type public.asset_type NOT NULL,
    title character varying(100) NOT NULL,
    description text,
    source public.asset_source DEFAULT 'upload'::public.asset_source NOT NULL,
    status public.asset_status DEFAULT 'ready'::public.asset_status NOT NULL,
    is_system boolean DEFAULT false NOT NULL,
    is_public boolean DEFAULT false NOT NULL,
    file_url character varying(500),
    file_size_bytes bigint,
    file_mime_type character varying(100),
    preview_url character varying(500),
    thumbnail_url character varying(500),
    content text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    generation_task_id character varying(100),
    generation_prompt text,
    generation_error text,
    use_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT assets_content_check CHECK ((((type = 'script'::public.asset_type) AND (content IS NOT NULL)) OR ((type <> 'script'::public.asset_type) AND (file_url IS NOT NULL))))
);


--
-- Name: TABLE assets; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.assets IS '资产表：存储形象、音色、脚本三种类型的素材';


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid,
    action character varying(100) NOT NULL,
    resource_type character varying(50),
    resource_id uuid,
    details jsonb,
    ip_address inet,
    user_agent text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE audit_logs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.audit_logs IS '审计日志表：记录用户操作用于安全审计';


--
-- Name: project_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id uuid NOT NULL,
    level character varying(20) DEFAULT 'info'::character varying NOT NULL,
    step character varying(100),
    message text NOT NULL,
    details jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE project_logs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.project_logs IS '项目日志表：记录视频生成过程的详细日志';


--
-- Name: projects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.projects (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    title character varying(200) NOT NULL,
    status public.project_status DEFAULT 'pending'::public.project_status NOT NULL,
    progress integer DEFAULT 0 NOT NULL,
    current_step character varying(100),
    avatar_id uuid NOT NULL,
    voice_id uuid NOT NULL,
    script_id uuid,
    script_content text,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    video_url character varying(500),
    audio_url character varying(500),
    thumbnail_url character varying(500),
    duration_seconds numeric(10,2),
    resolution public.video_resolution,
    file_size_bytes bigint,
    tts_task_id character varying(100),
    video_task_id character varying(100),
    error_message text,
    error_code character varying(50),
    retry_count integer DEFAULT 0 NOT NULL,
    credits_used numeric(10,4) DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    CONSTRAINT projects_progress_check CHECK (((progress >= 0) AND (progress <= 100))),
    CONSTRAINT projects_script_check CHECK (((script_id IS NOT NULL) OR (script_content IS NOT NULL)))
);


--
-- Name: TABLE projects; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.projects IS '项目表：存储视频生成任务及结果';


--
-- Name: subscription_plans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription_plans (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tier public.user_tier NOT NULL,
    name character varying(50) NOT NULL,
    description text,
    price_monthly numeric(10,2) DEFAULT 0 NOT NULL,
    price_yearly numeric(10,2) DEFAULT 0 NOT NULL,
    currency character varying(3) DEFAULT 'CNY'::character varying NOT NULL,
    minutes_per_month integer NOT NULL,
    storage_mb integer NOT NULL,
    max_resolution public.video_resolution DEFAULT '480p'::public.video_resolution NOT NULL,
    max_assets integer DEFAULT 100 NOT NULL,
    features jsonb DEFAULT '{}'::jsonb NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE subscription_plans; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.subscription_plans IS '订阅计划表：定义不同等级的功能和额度';


--
-- Name: system_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_configs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    key character varying(100) NOT NULL,
    value jsonb NOT NULL,
    description text,
    category character varying(50),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE system_configs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.system_configs IS '系统配置表：存储可动态调整的系统参数';


--
-- Name: task_queue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_queue (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    task_type character varying(50) NOT NULL,
    project_id uuid,
    payload jsonb NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    priority integer DEFAULT 0 NOT NULL,
    worker_id character varying(100),
    attempts integer DEFAULT 0 NOT NULL,
    max_attempts integer DEFAULT 3 NOT NULL,
    last_error text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    scheduled_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone
);


--
-- Name: TABLE task_queue; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.task_queue IS '任务队列表：用于异步任务调度（可用Redis替代）';


--
-- Name: user_api_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_api_configs (
    id uuid NOT NULL,
    user_id uuid,
    category character varying(30) NOT NULL,
    provider character varying(50) NOT NULL,
    config_data text NOT NULL,
    display_name character varying(100),
    is_active boolean NOT NULL,
    is_default boolean NOT NULL,
    is_system boolean NOT NULL,
    is_validated boolean NOT NULL,
    last_validated_at timestamp with time zone,
    validation_error text,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: user_oauth_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_oauth_accounts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    provider public.oauth_provider NOT NULL,
    provider_user_id character varying(255) NOT NULL,
    provider_username character varying(255),
    provider_email character varying(255),
    provider_avatar_url character varying(500),
    access_token text,
    refresh_token text,
    token_expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE user_oauth_accounts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_oauth_accounts IS 'OAuth账户关联表：支持GitHub等第三方登录';


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sessions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    token_hash character varying(64) NOT NULL,
    device_info jsonb,
    is_valid boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone
);


--
-- Name: TABLE user_sessions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_sessions IS '用户会话表：用于JWT Token管理和黑名单';


--
-- Name: user_usage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_usage (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    billing_cycle_start date NOT NULL,
    billing_cycle_end date NOT NULL,
    videos_generated integer DEFAULT 0 NOT NULL,
    minutes_used numeric(10,2) DEFAULT 0 NOT NULL,
    storage_used_bytes bigint DEFAULT 0 NOT NULL,
    api_calls integer DEFAULT 0 NOT NULL,
    minutes_limit numeric(10,2) NOT NULL,
    storage_limit_bytes bigint NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE user_usage; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_usage IS '用户用量表：按计费周期统计用户使用量';


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(255),
    password_hash character varying(255),
    avatar_url character varying(500),
    tier public.user_tier DEFAULT 'free'::public.user_tier NOT NULL,
    tier_expires_at timestamp with time zone,
    is_active boolean DEFAULT true NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at timestamp with time zone
);


--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.users IS '用户表：存储用户基本信息和订阅状态';


--
-- Name: v_project_detail; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_project_detail AS
 SELECT p.id,
    p.user_id,
    p.title,
    p.status,
    p.progress,
    p.current_step,
    p.video_url,
    p.audio_url,
    p.thumbnail_url,
    p.duration_seconds,
    p.resolution,
    p.config,
    p.error_message,
    p.created_at,
    p.completed_at,
    json_build_object('id', aa.id, 'title', aa.title, 'file_url', aa.file_url) AS avatar,
    json_build_object('id', av.id, 'title', av.title, 'file_url', av.file_url) AS voice,
        CASE
            WHEN (p.script_id IS NOT NULL) THEN json_build_object('id', as_.id, 'title', as_.title, 'content', as_.content)
            ELSE json_build_object('content', p.script_content)
        END AS script
   FROM (((public.projects p
     JOIN public.assets aa ON ((p.avatar_id = aa.id)))
     JOIN public.assets av ON ((p.voice_id = av.id)))
     LEFT JOIN public.assets as_ ON ((p.script_id = as_.id)));


--
-- Name: v_user_overview; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_user_overview AS
 SELECT u.id,
    u.username,
    u.email,
    u.avatar_url,
    u.tier,
    u.is_active,
    u.created_at,
    u.last_login_at,
    COALESCE(uu.videos_generated, 0) AS videos_generated,
    COALESCE(uu.minutes_used, (0)::numeric) AS minutes_used,
    COALESCE(uu.minutes_limit, (0)::numeric) AS minutes_limit,
    COALESCE(uu.storage_used_bytes, (0)::bigint) AS storage_used_bytes,
    COALESCE(uu.storage_limit_bytes, (0)::bigint) AS storage_limit_bytes,
    ( SELECT count(*) AS count
           FROM public.assets a
          WHERE (a.user_id = u.id)) AS total_assets,
    ( SELECT count(*) AS count
           FROM public.projects p
          WHERE (p.user_id = u.id)) AS total_projects
   FROM (public.users u
     LEFT JOIN public.user_usage uu ON (((u.id = uu.user_id) AND (uu.billing_cycle_start <= CURRENT_DATE) AND (uu.billing_cycle_end > CURRENT_DATE))));


--
-- Name: asset_tags asset_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_tags
    ADD CONSTRAINT asset_tags_pkey PRIMARY KEY (id);


--
-- Name: assets assets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: project_logs project_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_logs
    ADD CONSTRAINT project_logs_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: subscription_plans subscription_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_pkey PRIMARY KEY (id);


--
-- Name: subscription_plans subscription_plans_tier_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_tier_key UNIQUE (tier);


--
-- Name: system_configs system_configs_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_configs
    ADD CONSTRAINT system_configs_key_key UNIQUE (key);


--
-- Name: system_configs system_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_configs
    ADD CONSTRAINT system_configs_pkey PRIMARY KEY (id);


--
-- Name: task_queue task_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_queue
    ADD CONSTRAINT task_queue_pkey PRIMARY KEY (id);


--
-- Name: asset_tags unique_asset_tag; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_tags
    ADD CONSTRAINT unique_asset_tag UNIQUE (asset_id, tag);


--
-- Name: user_oauth_accounts unique_provider_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_oauth_accounts
    ADD CONSTRAINT unique_provider_user UNIQUE (provider, provider_user_id);


--
-- Name: user_usage unique_user_billing_cycle; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_usage
    ADD CONSTRAINT unique_user_billing_cycle UNIQUE (user_id, billing_cycle_start);


--
-- Name: user_oauth_accounts unique_user_provider; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_oauth_accounts
    ADD CONSTRAINT unique_user_provider UNIQUE (user_id, provider);


--
-- Name: user_api_configs uq_user_category_provider; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_api_configs
    ADD CONSTRAINT uq_user_category_provider UNIQUE (user_id, category, provider);


--
-- Name: user_api_configs user_api_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_api_configs
    ADD CONSTRAINT user_api_configs_pkey PRIMARY KEY (id);


--
-- Name: user_oauth_accounts user_oauth_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_oauth_accounts
    ADD CONSTRAINT user_oauth_accounts_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: user_usage user_usage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_usage
    ADD CONSTRAINT user_usage_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_asset_tags_asset_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_asset_tags_asset_id ON public.asset_tags USING btree (asset_id);


--
-- Name: idx_asset_tags_tag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_asset_tags_tag ON public.asset_tags USING btree (tag);


--
-- Name: idx_assets_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assets_created_at ON public.assets USING btree (created_at);


--
-- Name: idx_assets_is_system; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assets_is_system ON public.assets USING btree (is_system) WHERE (is_system = true);


--
-- Name: idx_assets_metadata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assets_metadata ON public.assets USING gin (metadata);


--
-- Name: idx_assets_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assets_status ON public.assets USING btree (status);


--
-- Name: idx_assets_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assets_type ON public.assets USING btree (type);


--
-- Name: idx_assets_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_assets_user_id ON public.assets USING btree (user_id) WHERE (user_id IS NOT NULL);


--
-- Name: idx_audit_logs_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_action ON public.audit_logs USING btree (action);


--
-- Name: idx_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: idx_audit_logs_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_resource ON public.audit_logs USING btree (resource_type, resource_id);


--
-- Name: idx_audit_logs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: idx_oauth_provider; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_oauth_provider ON public.user_oauth_accounts USING btree (provider, provider_user_id);


--
-- Name: idx_oauth_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_oauth_user_id ON public.user_oauth_accounts USING btree (user_id);


--
-- Name: idx_project_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_logs_created_at ON public.project_logs USING btree (created_at);


--
-- Name: idx_project_logs_level; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_logs_level ON public.project_logs USING btree (level);


--
-- Name: idx_project_logs_project_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_logs_project_id ON public.project_logs USING btree (project_id);


--
-- Name: idx_projects_avatar_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_avatar_id ON public.projects USING btree (avatar_id);


--
-- Name: idx_projects_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_created_at ON public.projects USING btree (created_at DESC);


--
-- Name: idx_projects_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_status ON public.projects USING btree (status);


--
-- Name: idx_projects_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_user_id ON public.projects USING btree (user_id);


--
-- Name: idx_projects_user_status_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_user_status_created ON public.projects USING btree (user_id, status, created_at DESC);


--
-- Name: idx_projects_voice_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_projects_voice_id ON public.projects USING btree (voice_id);


--
-- Name: idx_sessions_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_expires_at ON public.user_sessions USING btree (expires_at);


--
-- Name: idx_sessions_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_token_hash ON public.user_sessions USING btree (token_hash) WHERE (is_valid = true);


--
-- Name: idx_sessions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sessions_user_id ON public.user_sessions USING btree (user_id);


--
-- Name: idx_system_configs_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_system_configs_category ON public.system_configs USING btree (category);


--
-- Name: idx_system_configs_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_system_configs_key ON public.system_configs USING btree (key);


--
-- Name: idx_task_queue_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_task_queue_priority ON public.task_queue USING btree (priority DESC, created_at) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_task_queue_scheduled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_task_queue_scheduled ON public.task_queue USING btree (scheduled_at) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_task_queue_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_task_queue_status ON public.task_queue USING btree (status);


--
-- Name: idx_task_queue_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_task_queue_type ON public.task_queue USING btree (task_type);


--
-- Name: idx_usage_billing_cycle; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_billing_cycle ON public.user_usage USING btree (billing_cycle_start, billing_cycle_end);


--
-- Name: idx_usage_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_usage_user_id ON public.user_usage USING btree (user_id);


--
-- Name: idx_users_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_created_at ON public.users USING btree (created_at);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email) WHERE (email IS NOT NULL);


--
-- Name: idx_users_tier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_tier ON public.users USING btree (tier);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_username ON public.users USING btree (username);


--
-- Name: ix_user_api_configs_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_api_configs_category ON public.user_api_configs USING btree (category);


--
-- Name: ix_user_api_configs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_api_configs_user_id ON public.user_api_configs USING btree (user_id);


--
-- Name: assets update_assets_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_assets_updated_at BEFORE UPDATE ON public.assets FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: projects update_projects_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON public.projects FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: subscription_plans update_subscription_plans_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_subscription_plans_updated_at BEFORE UPDATE ON public.subscription_plans FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: system_configs update_system_configs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_system_configs_updated_at BEFORE UPDATE ON public.system_configs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: task_queue update_task_queue_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_task_queue_updated_at BEFORE UPDATE ON public.task_queue FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: user_oauth_accounts update_user_oauth_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_user_oauth_updated_at BEFORE UPDATE ON public.user_oauth_accounts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: user_usage update_user_usage_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_user_usage_updated_at BEFORE UPDATE ON public.user_usage FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: asset_tags asset_tags_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_tags
    ADD CONSTRAINT asset_tags_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;


--
-- Name: assets assets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.assets
    ADD CONSTRAINT assets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: project_logs project_logs_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_logs
    ADD CONSTRAINT project_logs_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: projects projects_avatar_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_avatar_id_fkey FOREIGN KEY (avatar_id) REFERENCES public.assets(id) ON DELETE RESTRICT;


--
-- Name: projects projects_script_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_script_id_fkey FOREIGN KEY (script_id) REFERENCES public.assets(id) ON DELETE SET NULL;


--
-- Name: projects projects_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: projects projects_voice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_voice_id_fkey FOREIGN KEY (voice_id) REFERENCES public.assets(id) ON DELETE RESTRICT;


--
-- Name: task_queue task_queue_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_queue
    ADD CONSTRAINT task_queue_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE CASCADE;


--
-- Name: user_api_configs user_api_configs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_api_configs
    ADD CONSTRAINT user_api_configs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_oauth_accounts user_oauth_accounts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_oauth_accounts
    ADD CONSTRAINT user_oauth_accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_usage user_usage_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_usage
    ADD CONSTRAINT user_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

