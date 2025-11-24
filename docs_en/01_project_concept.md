# Business and System Concept Document
## TechCore Solutions TMS Development Project

**Document Version**: 1.0
**Created Date**: November 23, 2025
**Status**: Draft

---

## 1. Project Background

### 1.1 Current Challenges
- **Cost Issues**: High running costs from external TMS services such as PayConnect
- **Technical Capability Enhancement**: Need to accumulate internal technical expertise and know-how through in-house development
- **Flexibility**: Need to implement unique features not achievable with external services

### 1.2 Development Decision Background
- Initially considered using PayConnect TMS 2.0
- Cost analysis determined that in-house development on AWS/Azure is more cost-effective in the long term
- Aiming to enhance internal technical capabilities and implement differentiated features

---

## 2. Project Objectives (Why)

### 2.1 Primary Objectives
1. **Cost Reduction**: Reduce external service costs (Target: 50%+ cost reduction)
2. **Technical Capability Enhancement**: Accumulate TMS development and operation know-how in-house
3. **Differentiated Features**: Implement value-added features not available from competitors
4. **Scalability**: Flexible design capable of supporting terminals beyond TC-200

### 2.2 Business Goals
- Optimize terminal management costs
- Rapid response when deploying new terminals
- Improve customer satisfaction (reduce incident response time)

---

## 3. Scope Definition

### 3.1 In Scope
| Category | Content |
|---------|------|
| **Target Terminals** | - TechCore Solutions TC-200 (initial support)<br>- Ensure scalability for future support of other manufacturers' terminals |
| **Core Features** | - Terminal registration and authentication management<br>- Firmware OTA updates<br>- Application distribution<br>- Parameter configuration changes<br>- Remote Key Injection (RKI)<br>- Terminal monitoring and diagnostics<br>- Reporting and analytics<br>- Differentiated features (described below) |
| **Users** | - System administrators<br>- Operations operators<br>- Merchant administrators<br>- Support staff |
| **System Infrastructure** | - Cloud (AWS or Azure)<br>- Web management console<br>- REST API |

### 3.2 Out of Scope
- Payment processing functionality itself
- Terminal hardware manufacturing and repair management
- Integration with inventory management systems (excluded from Phase 1)

---

## 4. Target Users and Personas

### 4.1 User Segments

| User Type | Role | Team Size | Usage Frequency |
|-----------|------|-----------|-----------------|
| **System Administrator** | Overall TMS management and configuration | 2-3 people | Daily |
| **Operations Operator** | Daily terminal management and monitoring | 5-10 people | Daily |
| **Merchant Administrator** | Managing their own store terminals | 100-1000 stores | 1-2 times/week |
| **Support Staff** | Incident response and inquiry handling | 3-5 people | Daily |
| **Developer** | API usage and system integration | 5-10 people | As needed |

### 4.2 Key Personas

#### Persona 1: Operations Operator (Tanaka-san)
- **Background**: Operations team performing 24/7 terminal monitoring
- **Needs**:
  - Want to detect anomalies immediately
  - Want to operate multiple terminals in bulk
  - Want to simplify incident response procedures
- **Pain Points**:
  - Currently many manual checks are time-consuming
  - Need to monitor multiple systems

#### Persona 2: Merchant Administrator (Store Manager Suzuki)
- **Background**: Store owner managing multiple locations
- **Needs**:
  - Want to easily check terminal status
  - Want to receive immediate support during issues
- **Pain Points**:
  - Limited technical knowledge
  - Need to respond while being busy

---

## 5. Expected Implementation Benefits (KPIs)

### 5.1 Quantitative Benefits

| KPI Item | Current (As-Is) | Target (To-Be) | Measurement Method |
|---------|----------------|----------------|-------------------|
| **Operating Costs** | PayConnect fees 100% | 50% or less | Monthly cost comparison |
| **Terminal Configuration Time** | 30 min/unit | 5 min/unit | Work time measurement |
| **Incident Response Time** | Average 4 hours | Average 1 hour | Incident records |
| **Concurrent Manageable Terminals** | - | 10,000+ units | System performance measurement |
| **Downtime** | 10 hours/month | 1 hour or less/month | Monitoring system records |

### 5.2 Qualitative Benefits
- Enhancement of internal technical capabilities
- Increased customization flexibility
- Improved customer satisfaction
- Differentiation from competitors

---

## 6. Differentiation Strategy (Value-Added Features)

### 6.1 Differentiation Points Based on Competitive Analysis

| Differentiated Feature | Description | Competitive Advantage |
|----------------------|-------------|----------------------|
| **AI Predictive Maintenance** | Failure prediction using machine learning | Most competitors only offer reactive responses |
| **Japan Market Specialization** | Full PayNet/CardLink support | Complements weaknesses of overseas products |
| **No-Code Configuration** | Complex settings possible through GUI only | Operable without technical staff |
| **Real-Time Analytics** | Immediate analysis and visualization of transaction data | Faster business decision-making |
| **Multi-Tenant Support** | Manage multiple companies in one system | Enables B2B2C deployment |
| **Voice Assistant** | Voice commands for terminal operation and status checks | Hands-free operation |

### 6.2 MVP vs Future Features

#### Phase 1: MVP (3-6 months)
- Basic terminal management features
- Web management console
- Basic monitoring and alerts
- Firmware updates

#### Phase 2: Differentiated Features (6-12 months)
- AI predictive maintenance
- Advanced analytics
- Multi-tenant
- API publication

#### Phase 3: Advanced Features (12+ months)
- Voice assistant
- Blockchain integration
- IoT integration

---

## 7. Technology Stack (Recommended)

### 7.1 Architecture Selection Rationale

| Layer | Technology Choice | Selection Rationale |
|-------|------------------|---------------------|
| **Backend** | Java/Spring Boot | - Proven enterprise track record<br>- Rich security features<br>- Scalable for large systems |
| **API Layer** | REST + WebSocket | - REST is standard<br>- WebSocket for real-time communication |
| **Frontend** | React + TypeScript | - Component reusability<br>- Type safety<br>- Rich library ecosystem |
| **Database** | PostgreSQL + Redis | - Combined use of RDBMS and cache<br>- High performance |
| **Infrastructure** | AWS | - Proven track record<br>- Leverage managed services |
| **Monitoring** | CloudWatch + Datadog | - Detailed monitoring<br>- Alert functionality |

### 7.2 Learning Path for Beginners
1. **Foundational Knowledge** (2 weeks)
   - Web technology basics (HTTP, REST API)
   - Database basics (SQL)
   - Cloud basics (AWS)

2. **Implementation Technologies** (4 weeks)
   - Spring Boot tutorial
   - React basics
   - Docker introduction

3. **Practical Development** (ongoing)
   - Pair programming
   - Code review
   - Incremental feature implementation

---

## 8. Risks and Countermeasures

| Risk Item | Impact | Probability | Countermeasures |
|-----------|--------|-------------|-----------------|
| **Insufficient Technical Skills** | High | Medium | - Utilize external experts<br>- Phased development<br>- Comprehensive training |
| **Security Vulnerabilities** | High | Low | - Security audits<br>- PCI DSS compliance<br>- Regular vulnerability assessments |
| **Scalability Challenges** | Medium | Medium | - Cloud-native design<br>- Load testing |
| **Cost Overruns** | Medium | Low | - Phased releases<br>- Cost monitoring |

---

## 9. Project Team Structure (Proposal)

### 9.1 Recommended Structure

| Role | Headcount | Responsibilities |
|------|-----------|-----------------|
| **Project Manager** | 1 | Overall coordination, stakeholder management |
| **Tech Lead** | 1 | Technology selection, architecture design |
| **Backend Developers** | 2-3 | API, business logic implementation |
| **Frontend Developers** | 2 | UI development, UX implementation |
| **Infrastructure Engineer** | 1 | AWS environment setup, operations design |
| **QA Engineer** | 1 | Test design, quality management |
| **External Advisors** | As needed | Specialized knowledge provision |

### 9.2 Phase-Based Staffing Plan
- **Phase 1 (MVP)**: Minimum configuration (5 people)
- **Phase 2 (Expansion)**: Full team (8 people)
- **Phase 3 (Operations)**: Operations team (3 people)

---

## 10. Next Steps

### 10.1 Immediate Actions
1. [DONE] Business concept approval
2. [ ] Create As-Is/To-Be business flows
3. [ ] Begin detailed requirements definition
4. [ ] Conduct technical verification (PoC)
5. [ ] Assemble project team

### 10.2 Decision Items
- Cloud provider selection (AWS vs Azure)
- Final decision on development language
- External resource utilization policy
- Finalize MVP feature scope

---

## Appendix A: Market Research Summary

### Major Competitor TMS Feature Comparison

| Vendor | Strengths | Weaknesses | Price Range |
|--------|-----------|------------|-------------|
| PayStore Pro | Cloud, 13 million unit track record | High price | High |
| VeriPay | Global deployment | Difficult to customize | High |
| PayConnect TMS 2.0 | Firebase-based, integrated RKI | Limited track record in Japan | Medium |
| IngenPay TEM | Android support | Legacy feel | High |

### Differentiation Opportunities
1. **Japan Market Specialization**: PayNet/CardLink support
2. **Cost Advantage**: Lower costs through in-house development
3. **Customizability**: Feature additions based on needs
4. **Integration**: Deep integration with proprietary products (TC-200)

---

## Revision History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025/11/23 | Initial version | Claude Code |
