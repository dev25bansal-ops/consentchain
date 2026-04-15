"""Consent Notice Templates - Multilingual DPDP-compliant templates."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
import json

from pydantic import BaseModel, Field
from jinja2 import Template


class TemplateLanguage(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    BENGALI = "bn"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"


class TemplateCategory(str, Enum):
    CONSENT_REQUEST = "CONSENT_REQUEST"
    DATA_COLLECTION = "DATA_COLLECTION"
    THIRD_PARTY_SHARING = "THIRD_PARTY_SHARING"
    SENSITIVE_DATA = "SENSITIVE_DATA"
    MARKETING = "MARKETING"
    RESEARCH = "RESEARCH"
    SERVICE_DELIVERY = "SERVICE_DELIVERY"


class ConsentTemplate(BaseModel):
    id: UUID
    name: str
    language: TemplateLanguage
    category: TemplateCategory
    purpose: str
    data_types: List[str]
    content: str
    variables: List[str]
    version: int
    active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class TemplateCreate(BaseModel):
    name: str
    language: TemplateLanguage
    category: TemplateCategory
    purpose: str
    data_types: List[str]
    content: str


class TemplateRenderRequest(BaseModel):
    template_id: UUID
    variables: Dict[str, Any]


DEFAULT_TEMPLATES = {
    TemplateLanguage.ENGLISH: {
        TemplateCategory.CONSENT_REQUEST: """
# Consent Request Notice

## Digital Personal Data Protection Act, 2023

**Data Fiduciary:** {{ fiduciary_name }}

Dear {{ principal_name }},

We, {{ fiduciary_name }}, are requesting your consent to process your personal data for the following purposes:

### Purpose of Processing
{{ purpose }}

### Data Categories
The following categories of personal data will be processed:
{% for data_type in data_types %}
- {{ data_type }}
{% endfor %}

### Duration
Your consent will be valid for {{ duration }} from the date of granting.

### Your Rights
Under the DPDP Act, 2023, you have the right to:
1. Withdraw this consent at any time
2. Request access to your personal data
3. Request correction of inaccurate data
4. Request erasure of your personal data
5. File a grievance with our Grievance Officer

### Grievance Officer
Name: {{ grievance_officer_name }}
Contact: {{ grievance_officer_contact }}
Email: {{ grievance_officer_email }}

### Third-Party Sharing
{% if third_party_sharing %}
Your data may be shared with:
{% for party in third_parties %}
- {{ party.name }} ({{ party.purpose }})
{% endfor %}
{% else %}
Your data will not be shared with third parties.
{% endif %}

By providing consent, you acknowledge that you have read and understood this notice.

**Date:** {{ consent_date }}
**Reference ID:** {{ reference_id }}
""",
        TemplateCategory.SENSITIVE_DATA: """
# Sensitive Personal Data Consent Notice

## Digital Personal Data Protection Act, 2023

**IMPORTANT: This consent relates to SENSITIVE PERSONAL DATA**

**Data Fiduciary:** {{ fiduciary_name }}

Dear {{ principal_name }},

We are seeking your **explicit consent** for processing your **sensitive personal data** as defined under Section 2(t) of the DPDP Act, 2023.

### Sensitive Data Categories
{% for data_type in data_types %}
- **{{ data_type }}**
{% endfor %}

### Purpose of Processing
{{ purpose }}

### Legal Basis
We are processing this sensitive data based on your **explicit consent** under Section 7 of the DPDP Act.

### Additional Protections
1. Your sensitive data will be encrypted at rest and in transit
2. Access is restricted to authorized personnel only
3. Regular security audits are conducted
4. Data breach notification within 72 hours

### Retention Period
{{ retention_period }}

### Your Rights
You may withdraw this consent at any time. Withdrawal of consent will not affect the lawfulness of processing based on consent before its withdrawal.

### Contact for Queries
**Data Protection Officer:** {{ dpo_name }}
**Email:** {{ dpo_email }}
**Phone:** {{ dpo_phone }}

---

**By signing below, I provide my explicit consent for the processing described above.**

Signature: _________________
Date: {{ consent_date }}
""",
    },
    TemplateLanguage.HINDI: {
        TemplateCategory.CONSENT_REQUEST: """
# सहमति अनुरोध सूचना

## डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम, 2023

**डेटा फिड्यूशियरी:** {{ fiduciary_name }}

प्रिय {{ principal_name }},

हम, {{ fiduciary_name }}, आपकी व्यक्तिगत डेटा को निम्नलिखित उद्देश्यों के लिए संसाधित करने के लिए आपकी सहमति मांग रहे हैं:

### संसाधन का उद्देश्य
{{ purpose }}

### डेटा श्रेणियाँ
व्यक्तिगत डेटा की निम्नलिखित श्रेणियाँ संसाधित की जाएंगी:
{% for data_type in data_types %}
- {{ data_type }}
{% endfor %}

### अवधि
आपकी सहमति दिनांक से {{ duration }} तक वैध रहेगी।

### आपके अधिकार
डीपीडीपी अधिनियम, 2023 के तहत, आपको निम्नलिखित अधिकार हैं:
1. किसी भी समय इस सहमति को वापस लेना
2. अपने व्यक्तिगत डेटा तक पहुंच का अनुरोध करना
3. गलत डेटा को सही करने का अनुरोध करना
4. अपने व्यक्तिगत डेटा को मिटाने का अनुरोध करना
5. हमारे शिकायत अधिकारी के पास शिकायत दर्ज करना

### शिकायत अधिकारी
नाम: {{ grievance_officer_name }}
संपर्क: {{ grievance_officer_contact }}
ईमेल: {{ grievance_officer_email }}

---

**तारीख:** {{ consent_date }}
**संदर्भ आईडी:** {{ reference_id }}
""",
    },
}


class TemplateService:
    def __init__(self, db=None):
        self.db = db
        self.templates: Dict[UUID, ConsentTemplate] = {}
        self._initialized = False

    async def _ensure_initialized(self):
        if self._initialized:
            return
        await self._load_templates()
        self._initialized = True

    async def _load_templates(self):
        if self.db:
            from sqlalchemy import select
            from api.database import ConsentTemplateDB

            result = await self.db.execute(
                select(ConsentTemplateDB).where(ConsentTemplateDB.active == True)
            )
            db_templates = result.scalars().all()
            for t in db_templates:
                self.templates[t.id] = ConsentTemplate(
                    id=t.id,
                    name=t.name,
                    language=TemplateLanguage(t.language),
                    category=TemplateCategory(t.category),
                    purpose=t.purpose,
                    data_types=json.loads(t.default_data_types),
                    content=t.description,
                    variables=json.loads(t.required_fields) if t.required_fields else [],
                    version=t.version,
                    active=t.active,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )

        if not self.templates:
            self._load_default_templates()

    def _load_default_templates(self):
        for language, categories in DEFAULT_TEMPLATES.items():
            for category, content in categories.items():
                template_id = uuid4()
                self.templates[template_id] = ConsentTemplate(
                    id=template_id,
                    name=f"{category.value} - {language.value}",
                    language=language,
                    category=category,
                    purpose="Default template",
                    data_types=["PERSONAL_INFO"],
                    content=content.strip(),
                    variables=self._extract_variables(content),
                    version=1,
                    active=True,
                    created_at=datetime.now(timezone.utc),
                )

    def _extract_variables(self, content: str) -> List[str]:
        import re

        variables = re.findall(r"\{\{\s*(\w+)\s*\}\}", content)
        variables.extend(re.findall(r"\{%\s*for\s+(\w+)\s+in", content))
        return list(set(variables))

    async def get_template(self, template_id: UUID) -> Optional[ConsentTemplate]:
        await self._ensure_initialized()
        return self.templates.get(template_id)

    async def list_templates(
        self,
        language: Optional[TemplateLanguage] = None,
        category: Optional[TemplateCategory] = None,
    ) -> List[ConsentTemplate]:
        await self._ensure_initialized()
        templates = list(self.templates.values())

        if language:
            templates = [t for t in templates if t.language == language]
        if category:
            templates = [t for t in templates if t.category == category]

        return templates

    async def render_template(
        self,
        template_id: UUID,
        variables: Dict[str, Any],
    ) -> str:
        template = await self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        jinja_template = Template(template.content)
        return jinja_template.render(**variables)

    async def create_template(self, data: TemplateCreate) -> ConsentTemplate:
        await self._ensure_initialized()
        template_id = uuid4()
        template = ConsentTemplate(
            id=template_id,
            name=data.name,
            language=data.language,
            category=data.category,
            purpose=data.purpose,
            data_types=data.data_types,
            content=data.content,
            variables=self._extract_variables(data.content),
            version=1,
            active=True,
            created_at=datetime.now(timezone.utc),
        )

        self.templates[template_id] = template
        return template

    async def get_template_for_consent(
        self,
        purpose: str,
        data_types: List[str],
        language: TemplateLanguage = TemplateLanguage.ENGLISH,
        is_sensitive: bool = False,
    ) -> Optional[ConsentTemplate]:
        category = (
            TemplateCategory.SENSITIVE_DATA if is_sensitive else TemplateCategory.CONSENT_REQUEST
        )

        templates = await self.list_templates(language=language, category=category)

        if templates:
            return templates[0]

        all_templates = await self.list_templates(category=category)
        return all_templates[0] if all_templates else None


template_service = TemplateService()
