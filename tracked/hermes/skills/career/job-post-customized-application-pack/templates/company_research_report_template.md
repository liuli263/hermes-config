# 公司调研固定输出模板

> 公司：{{ company_name }}
> 职位：{{ position_name }}
> 调研范围：{{ region_scope }}
> 调研日期：{{ research_date }}

## 1. 一页摘要
- **是否值得投递**：{{ recommendation }}
- **综合评分（10分制）**：{{ overall_score }}
- **核心结论**：{{ executive_summary }}
- **与用户偏好的匹配**：
  - 通勤（Kirkland 30 分钟内）：{{ commute_fit }}
  - 薪资（>= 20 CAD/h）：{{ pay_fit }}
  - 英语优先：{{ english_fit }}
  - 远程/混合：{{ remote_fit }}
  - 福利/年假：{{ benefits_fit }}

## 2. 基础信息
| 信息项 | 结果 | 来源 | 可信度 |
|---|---|---|---|
| 公司全称 | {{ legal_name }} | {{ source_legal_name }} | {{ conf_legal_name }} |
| 官网 | {{ official_site }} | {{ source_official_site }} | {{ conf_official_site }} |
| LinkedIn | {{ linkedin_url }} | {{ source_linkedin }} | {{ conf_linkedin }} |
| 总部 | {{ headquarters }} | {{ source_headquarters }} | {{ conf_headquarters }} |
| 加拿大办公地点 | {{ canada_locations }} | {{ source_canada_locations }} | {{ conf_canada_locations }} |
| 公司规模 | {{ company_size }} | {{ source_company_size }} | {{ conf_company_size }} |
| 行业/主营业务 | {{ industry_summary }} | {{ source_industry_summary }} | {{ conf_industry_summary }} |
| 是否上市 | {{ public_status }} | {{ source_public_status }} | {{ conf_public_status }} |
| 近一年动态 | {{ business_updates }} | {{ source_business_updates }} | {{ conf_business_updates }} |

## 3. 招聘与岗位情况
| 信息项 | 结果 | 来源 | 可信度 |
|---|---|---|---|
| 加拿大是否在招 | {{ hiring_in_canada }} | {{ source_hiring_in_canada }} | {{ conf_hiring_in_canada }} |
| 常见招聘城市 | {{ hiring_cities }} | {{ source_hiring_cities }} | {{ conf_hiring_cities }} |
| 常见岗位 | {{ common_roles }} | {{ source_common_roles }} | {{ conf_common_roles }} |
| 工作模式 | {{ work_mode }} | {{ source_work_mode }} | {{ conf_work_mode }} |
| 工签/LMIA/担保 | {{ sponsorship }} | {{ source_sponsorship }} | {{ conf_sponsorship }} |
| 招聘页 | {{ careers_url }} | {{ source_careers_url }} | {{ conf_careers_url }} |
| 招聘稳定性 | {{ hiring_stability }} | {{ source_hiring_stability }} | {{ conf_hiring_stability }} |

## 4. 员工评价与口碑
- **Glassdoor / Indeed / Reddit 综合印象**：{{ reputation_summary }}
- **主要优点**：
  - {{ pros_1 }}
  - {{ pros_2 }}
  - {{ pros_3 }}
- **主要缺点**：
  - {{ cons_1 }}
  - {{ cons_2 }}
  - {{ cons_3 }}
- **员工流动/稳定性**：{{ attrition_notes }}
- **论坛高频关键词**：{{ forum_keywords }}

## 5. 薪资情况
| 岗位 | 地区 | Base | Bonus/Equity | Total Comp | 来源 | 可信度 |
|---|---|---|---|---|---|---|
| {{ salary_role_1 }} | {{ salary_region_1 }} | {{ salary_base_1 }} | {{ salary_bonus_1 }} | {{ salary_tc_1 }} | {{ salary_source_1 }} | {{ salary_conf_1 }} |
| {{ salary_role_2 }} | {{ salary_region_2 }} | {{ salary_base_2 }} | {{ salary_bonus_2 }} | {{ salary_tc_2 }} | {{ salary_source_2 }} | {{ salary_conf_2 }} |

## 6. 福利待遇
| 福利项 | 状态（已确认/未确认/员工提及） | 结果 | 来源 | 可信度 |
|---|---|---|---|---|
| Extended Health | {{ health_status }} | {{ health_notes }} | {{ health_source }} | {{ health_conf }} |
| Dental | {{ dental_status }} | {{ dental_notes }} | {{ dental_source }} | {{ dental_conf }} |
| Vision | {{ vision_status }} | {{ vision_notes }} | {{ vision_source }} | {{ vision_conf }} |
| RRSP / Pension | {{ rrsp_status }} | {{ rrsp_notes }} | {{ rrsp_source }} | {{ rrsp_conf }} |
| Vacation days | {{ vacation_status }} | {{ vacation_notes }} | {{ vacation_source }} | {{ vacation_conf }} |
| Sick leave | {{ sick_status }} | {{ sick_notes }} | {{ sick_source }} | {{ sick_conf }} |
| Bonus | {{ bonus_status }} | {{ bonus_notes }} | {{ bonus_source }} | {{ bonus_conf }} |
| Remote policy | {{ remote_status }} | {{ remote_notes }} | {{ remote_source }} | {{ remote_conf }} |
| Flexible schedule | {{ flex_status }} | {{ flex_notes }} | {{ flex_source }} | {{ flex_conf }} |

## 7. 面试流程
- **常见流程**：{{ interview_process }}
- **轮次**：{{ interview_rounds }}
- **难度**：{{ interview_difficulty }}
- **常见题型**：{{ interview_topics }}
- **是否有 take-home**：{{ take_home }}
- **是否有背调/reference check**：{{ background_check }}
- **面试体验**：{{ interview_experience }}

## 8. 风险排查
- **裁员/冻结招聘**：{{ layoff_notes }}
- **劳动纠纷/诉讼**：{{ legal_risk_notes }}
- **管理层变动**：{{ leadership_notes }}
- **财务/组织稳定性**：{{ stability_notes }}
- **高频差评关键词**：{{ negative_keywords }}
- **加拿大实体存在性**：{{ canada_entity_check }}

## 9. 适合度判断
- **更适合哪类求职者**：{{ fit_candidate_types }}
- **主要优点（3-5条）**：{{ key_strengths }}
- **主要风险（3-5条）**：{{ key_risks }}
- **最终建议**：{{ final_recommendation }}

## 10. 来源清单
### 官网
- {{ source_official_1 }}
- {{ source_official_2 }}

### LinkedIn
- {{ source_linkedin_1 }}

### Glassdoor / Indeed
- {{ source_reviews_1 }}
- {{ source_reviews_2 }}

### Reddit / 社区
- {{ source_reddit_1 }}

### 新闻 / 企业注册
- {{ source_news_1 }}
- {{ source_registry_1 }}
