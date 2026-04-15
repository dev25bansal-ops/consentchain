from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import logging
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    BENGALI = "bn"
    TELUGU = "te"
    MARATHI = "mr"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"


@dataclass
class ConsentTerm:
    term_id: str
    translations: Dict[str, str]
    description: Dict[str, str]


@dataclass
class ConsentTemplate:
    template_id: str
    category: str
    language: Language
    title: str
    summary: str
    full_text: str
    terms: List[str]
    data_types: List[str]
    purpose: str
    duration_days: int
    version: str


CONSENT_TERMS: Dict[str, ConsentTerm] = {
    "personal_info": ConsentTerm(
        term_id="personal_info",
        translations={
            "en": "Personal Information",
            "hi": "व्यक्तिगत जानकारी",
            "ta": "தனிப்பட்ட தகவல்",
            "bn": "ব্যক্তিগত তথ্য",
        },
        description={
            "en": "Your name, date of birth, and other identifying details",
            "hi": "आपका नाम, जन्म तिथि, और अन्य पहचान करने वाले विवरण",
            "ta": "உங்கள் பெயர், பிறந்த தேதி மற்றும் பிற அடையாள விவரங்கள்",
            "bn": "আপনার নাম, জন্ম তারিখ এবং অন্যান্য পরিচয়ের বিবরণ",
        },
    ),
    "contact_info": ConsentTerm(
        term_id="contact_info",
        translations={
            "en": "Contact Information",
            "hi": "संपर्क जानकारी",
            "ta": "தொடர்பு தகவல்",
            "bn": "যোগাযোগের তথ্য",
        },
        description={
            "en": "Your email address, phone number, and postal address",
            "hi": "आपका ईमेल पता, फोन नंबर, और डाक पता",
            "ta": "உங்கள் மின்னஞ்சல் முகவரி, தொலைபேசி எண் மற்றும் அஞ்சல் முகவரி",
            "bn": "আপনার ইমেইল ঠিকানা, ফোন নম্বর এবং ডাক ঠিকানা",
        },
    ),
    "financial_data": ConsentTerm(
        term_id="financial_data",
        translations={
            "en": "Financial Information",
            "hi": "वित्तीय जानकारी",
            "ta": "நிதி தகவல்",
            "bn": "আর্থিক তথ্য",
        },
        description={
            "en": "Your bank account details, transaction history, and credit information",
            "hi": "आपके बैंक खाते का विवरण, लेनदेन इतिहास, और क्रेडिट जानकारी",
            "ta": "உங்கள் வங்கி கணக்கு விவரங்கள், பரிவர்த்தனை வரலாறு மற்றும் கடன் தகவல்",
            "bn": "আপনার ব্যাংক অ্যাকাউন্টের বিবরণ, লেনদেনের ইতিহাস এবং ক্রেডিট তথ্য",
        },
    ),
    "health_data": ConsentTerm(
        term_id="health_data",
        translations={
            "en": "Health Information",
            "hi": "स्वास्थ्य जानकारी",
            "ta": "சுகாதார தகவல்",
            "bn": "স্বাস্থ্য তথ্য",
        },
        description={
            "en": "Your medical records, prescriptions, and health conditions",
            "hi": "आपके चिकित्सा रिकॉर्ड, प्रिस्क्रिप्शन, और स्वास्थ्य स्थितियां",
            "ta": "உங்கள் மருத்துவ பதிவுகள், மருந்துகள் மற்றும் சுகாதார நிலைகள்",
            "bn": "আপনার চিকিৎসা রেকর্ড, প্রেসক্রিপশন এবং স্বাস্থ্যের অবস্থা",
        },
    ),
    "location_data": ConsentTerm(
        term_id="location_data",
        translations={
            "en": "Location Information",
            "hi": "स्थान जानकारी",
            "ta": "இருப்பிட தகவல்",
            "bn": "অবস্থানের তথ্য",
        },
        description={
            "en": "Your GPS location and movement patterns",
            "hi": "आपकी जीपीएस स्थान और आंदोलन पैटर्न",
            "ta": "உங்கள் ஜிபிஎஸ் இருப்பிடம் மற்றும் இயக்க முறைகள்",
            "bn": "আপনার জিপিএস অবস্থান এবং চলাচলের ধরণ",
        },
    ),
}


CONSENT_TEMPLATES: Dict[str, Dict[Language, ConsentTemplate]] = {
    "marketing_consent": {
        Language.ENGLISH: ConsentTemplate(
            template_id="marketing_consent",
            category="MARKETING",
            language=Language.ENGLISH,
            title="Marketing Communications Consent",
            summary="I agree to receive promotional messages and marketing materials.",
            full_text="""Marketing Communications Consent

I, the Data Principal, hereby provide my consent to {fiduciary_name} to use my personal information for marketing purposes.

Data Types Covered:
{data_types_list}

Purpose:
I consent to receive promotional communications, newsletters, and marketing offers via:
- Email
- SMS/WhatsApp
- Phone calls (during permitted hours)

Duration:
This consent is valid for {duration_days} days from the date of grant.

Your Rights:
- You may withdraw this consent at any time
- You have the right to access your data
- You have the right to request deletion

By granting this consent, you confirm that you have read and understood the terms above.""",
            terms=["marketing", "promotional", "communications"],
            data_types=["contact_info", "personal_info"],
            purpose="MARKETING",
            duration_days=365,
            version="1.0",
        ),
        Language.HINDI: ConsentTemplate(
            template_id="marketing_consent",
            category="MARKETING",
            language=Language.HINDI,
            title="विपणन संचार सहमति",
            summary="मैं प्रचार संदेश और विपणन सामग्री प्राप्त करने के लिए सहमत हूं।",
            full_text="""विपणन संचार सहमति

मैं, डेटा प्रधान, इसके द्वारा {fiduciary_name} को विपणन उद्देश्यों के लिए अपनी व्यक्तिगत जानकारी का उपयोग करने की अपनी सहमति प्रदान करता/करती हूं।

शामिल डेटा प्रकार:
{data_types_list}

उद्देश्य:
मैं प्रचारात्मक संचार, समाचार पत्र, और विपणन प्रस्ताव प्राप्त करने के लिए सहमत हूं:
- ईमेल
- एसएमएस/व्हाट्सएप
- फोन कॉल (अनुमत समय के दौरान)

अवधि:
यह सहमति अनुदान की तारीख से {duration_days} दिनों के लिए मान्य है।

आपके अधिकार:
- आप किसी भी समय इस सहमति को वापस ले सकते हैं
- आपको अपना डेटा एक्सेस करने का अधिकार है
- आपको हटाने का अनुरोध करने का अधिकार है

इस सहमति को प्रदान करके, आप पुष्टि करते हैं कि आपने ऊपर दिए गए नियमों को पढ़ा और समझा है।""",
            terms=["विपणन", "प्रचारात्मक", "संचार"],
            data_types=["contact_info", "personal_info"],
            purpose="MARKETING",
            duration_days=365,
            version="1.0",
        ),
        Language.TAMIL: ConsentTemplate(
            template_id="marketing_consent",
            category="MARKETING",
            language=Language.TAMIL,
            title="சந்தைப்படுத்தல் தகவல்தொடர்பு ஒப்புதல்",
            summary="விளம்பர செய்திகள் மற்றும் சந்தைப்படுத்தல் பொருட்களைப் பெற நான் ஒப்புக்கொள்கிறேன்.",
            full_text="""சந்தைப்படுத்தல் தகவல்தொடர்பு ஒப்புதல்

நான், தரவு அதிபர், சந்தைப்படுத்தல் நோக்கங்களுக்காக எனது தனிப்பட்ட தகவலைப் பயன்படுத்த {fiduciary_name} க்கு எனது ஒப்புதலை இதன் மூலம் வழங்குகிறேன்.

உள்ளடக்கிய தரவு வகைகள்:
{data_types_list}

நோக்கம்:
விளம்பர தகவல்தொடர்புகள், செய்திமடல்கள் மற்றும் சந்தைப்படுத்தல் சலுகைகளைப் பெற நான் ஒப்புக்கொள்கிறேன்:
- மின்னஞ்சல்
- எஸ்எம்எஸ்/வாட்ஸ்அப்
- தொலைபேசி அழைப்புகள் (அனுமதிக்கப்பட்ட நேரத்தில்)

காலம்:
இந்த ஒப்புதல் வழங்கப்பட்ட தேதி முதல் {duration_days} நாட்கள் செல்லுபடியாகும்.

உங்கள் உரிமைகள்:
- நீங்கள் எப்போது வேண்டுமானாலும் இந்த ஒப்புதலை திரும்பப் பெறலாம்
- உங்கள் தரவை அணுக உங்களுக்கு உரிமை உண்டு
- நீக்கம் கோர உங்களுக்கு உரிமை உண்டு

இந்த ஒப்புதலை வழங்குவதன் மூலம், மேலே உள்ள விதிகளை நீங்கள் படித்து புரிந்துகொண்டதாக உறுதிப்படுத்துகிறீர்கள்.""",
            terms=["சந்தைப்படுத்தல்", "விளம்பர", "தகவல்தொடர்பு"],
            data_types=["contact_info", "personal_info"],
            purpose="MARKETING",
            duration_days=365,
            version="1.0",
        ),
        Language.BENGALI: ConsentTemplate(
            template_id="marketing_consent",
            category="MARKETING",
            language=Language.BENGALI,
            title="বিপণন যোগাযোগ সম্মতি",
            summary="আমি প্রচারমূলক বার্তা এবং বিপণন সামগ্রী পেতে সম্মত।",
            full_text="""বিপণন যোগাযোগ সম্মতি

আমি, তথ্য প্রধান, এর মাধ্যমে {fiduciary_name} কে বিপণন উদ্দেশ্যে আমার ব্যক্তিগত তথ্য ব্যবহার করার জন্য আমার সম্মতি প্রদান করছি।

অন্তর্ভুক্ত তথ্যের প্রকার:
{data_types_list}

উদ্দেশ্য:
আমি নিম্নলিখিত মাধ্যমে প্রচারমূলক যোগাযোগ, নিউজলেটার এবং বিপণন অফার পেতে সম্মত:
- ইমেইল
- এসএমএস/হোয়াটসঅ্যাপ
- ফোন কল (অনুমোদিত সময়ে)

সময়কাল:
এই সম্মতি প্রদানের তারিখ থেকে {duration_days} দিনের জন্য বৈধ।

আপনার অধিকার:
- আপনি যেকোনো সময় এই সম্মতি প্রত্যাহার করতে পারেন
- আপনার তথ্য অ্যাক্সেস করার অধিকার আপনার আছে
- আপনার মুছে ফেলার অনুরোধ করার অধিকার আছে

এই সম্মতি প্রদান করে, আপনি নিশ্চিত করছেন যে আপনি উপরের শর্তাবলী পড়েছেন এবং বুঝেছেন।""",
            terms=["বিপণন", "প্রচারমূলক", "যোগাযোগ"],
            data_types=["contact_info", "personal_info"],
            purpose="MARKETING",
            duration_days=365,
            version="1.0",
        ),
    },
    "service_delivery": {
        Language.ENGLISH: ConsentTemplate(
            template_id="service_delivery",
            category="SERVICE_DELIVERY",
            language=Language.ENGLISH,
            title="Service Delivery Consent",
            summary="I consent to the use of my data for service delivery purposes.",
            full_text="""Service Delivery Consent

I, the Data Principal, hereby provide my consent to {fiduciary_name} to process my personal information for service delivery.

Data Types Covered:
{data_types_list}

Purpose:
This consent allows processing of personal data necessary for:
- Account management
- Order processing
- Customer support
- Service improvements

Duration:
This consent is valid for {duration_days} days from the date of grant.

DPDP Act Rights:
Under the Digital Personal Data Protection Act 2023, you have the right to:
- Withdraw consent at any time
- Access your personal data
- Request correction of inaccurate data
- Request deletion of your data

By granting this consent, you confirm understanding of the above terms.""",
            terms=["service", "delivery", "processing"],
            data_types=["personal_info", "contact_info"],
            purpose="SERVICE_DELIVERY",
            duration_days=730,
            version="1.0",
        ),
        Language.HINDI: ConsentTemplate(
            template_id="service_delivery",
            category="SERVICE_DELIVERY",
            language=Language.HINDI,
            title="सेवा वितरण सहमति",
            summary="मैं सेवा वितरण उद्देश्यों के लिए अपने डेटा के उपयोग के लिए सहमत हूं।",
            full_text="""सेवा वितरण सहमति

मैं, डेटा प्रधान, सेवा वितरण के लिए अपनी व्यक्तिगत जानकारी को संसाधित करने के लिए {fiduciary_name} को अपनी सहमति प्रदान करता/करती हूं।

शामिल डेटा प्रकार:
{data_types_list}

उद्देश्य:
यह सहमति निम्नलिखित के लिए आवश्यक व्यक्तिगत डेटा के प्रसंस्करण की अनुमति देती है:
- खाता प्रबंधन
- ऑर्डर प्रसंस्करण
- ग्राहक सहायता
- सेवा सुधार

अवधि:
यह सहमति अनुदान की तारीख से {duration_days} दिनों के लिए मान्य है।

DPDP अधिनियम अधिकार:
डिजिटल व्यक्तिगत डेटा संरक्षण अधिनियम 2023 के तहत, आपको अधिकार है:
- किसी भी समय सहमति वापस लेने के लिए
- अपने व्यक्तिगत डेटा तक पहुंच
- गलत डेटा का सुधार अनुरोध करने के लिए
- अपने डेटा को हटाने का अनुरोध करने के लिए

इस सहमति को प्रदान करके, आप उपरोक्त शर्तों की समझ की पुष्टि करते हैं।""",
            terms=["सेवा", "वितरण", "प्रसंस्करण"],
            data_types=["personal_info", "contact_info"],
            purpose="SERVICE_DELIVERY",
            duration_days=730,
            version="1.0",
        ),
        Language.TAMIL: ConsentTemplate(
            template_id="service_delivery",
            category="SERVICE_DELIVERY",
            language=Language.TAMIL,
            title="சேவை வழங்கல் ஒப்புதல்",
            summary="சேவை வழங்கல் நோக்கங்களுக்காக எனது தரவைப் பயன்படுத்த நான் ஒப்புக்கொள்கிறேன்.",
            full_text="""சேவை வழங்கல் ஒப்புதல்

நான், தரவு அதிபர், சேவை வழங்கலுக்காக எனது தனிப்பட்ட தகவலைச் செயலாக்க {fiduciary_name} க்கு எனது ஒப்புதலை வழங்குகிறேன்.

உள்ளடக்கிய தரவு வகைகள்:
{data_types_list}

நோக்கம்:
இந்த ஒப்புதல் பின்வருவனவற்றிற்கு தேவையான தனிப்பட்ட தரவைச் செயலாக்க அனுமதிக்கிறது:
- கணக்கு மேலாண்மை
- ஆர்டர் செயலாக்கம்
- வாடிக்கையாளர் ஆதரவு
- சேவை மேம்பாடுகள்

காலம்:
இந்த ஒப்புதல் வழங்கப்பட்ட தேதி முதல் {duration_days} நாட்கள் செல்லுபடியாகும்.

DPDP சட்டம் உரிமைகள்:
டிஜிட்டல் தனிப்பட்ட தரவு பாதுகாப்புச் சட்டம் 2023-ன் கீழ், உங்களுக்கு உரிமை உண்டு:
- எப்போது வேண்டுமானாலும் ஒப்புதலை திரும்பப் பெற
- உங்கள் தனிப்பட்ட தரவை அணுக
- தவறான தரவைச் சரிசெய்ய கோர
- உங்கள் தரவை நீக்க கோர

இந்த ஒப்புதலை வழங்குவதன் மூலம், மேலே உள்ள விதிகளைப் புரிந்துகொண்டதாக உறுதிப்படுத்துகிறீர்கள்.""",
            terms=["சேவை", "வழங்கல்", "செயலாக்கம்"],
            data_types=["personal_info", "contact_info"],
            purpose="SERVICE_DELIVERY",
            duration_days=730,
            version="1.0",
        ),
        Language.BENGALI: ConsentTemplate(
            template_id="service_delivery",
            category="SERVICE_DELIVERY",
            language=Language.BENGALI,
            title="সেবা প্রদানের সম্মতি",
            summary="আমি সেবা প্রদানের উদ্দেশ্যে আমার তথ্য ব্যবহারে সম্মত।",
            full_text="""সেবা প্রদানের সম্মতি

আমি, তথ্য প্রধান, সেবা প্রদানের জন্য আমার ব্যক্তিগত তথ্য প্রক্রিয়া করার জন্য {fiduciary_name} কে আমার সম্মতি প্রদান করছি।

অন্তর্ভুক্ত তথ্যের প্রকার:
{data_types_list}

উদ্দেশ্য:
এই সম্মতি নিম্নলিখিতের জন্য প্রয়োজনীয় ব্যক্তিগত তথ্য প্রক্রিয়া করতে অনুমতি দেয়:
- অ্যাকাউন্ট ব্যবস্থাপনা
- অর্ডার প্রক্রিয়াকরণ
- গ্রাহক সহায়তা
- সেবা উন্নতি

সময়কাল:
এই সম্মতি প্রদানের তারিখ থেকে {duration_days} দিনের জন্য বৈধ।

DPDP আইন অধিকার:
ডিজিটাল ব্যক্তিগত তথ্য সুরক্ষা আইন ২০২৩-এর অধীনে, আপনার অধিকার আছে:
- যেকোনো সময় সম্মতি প্রত্যাহার করতে
- আপনার ব্যক্তিগত তথ্য অ্যাক্সেস করতে
- ভুল তথ্য সংশোধনের অনুরোধ করতে
- আপনার তথ্য মুছে ফেলার অনুরোধ করতে

এই সম্মতি প্রদান করে, আপনি উপরের শর্তাবলী বুঝেছেন বলে নিশ্চিত করছেন।""",
            terms=["সেবা", "প্রদান", "প্রক্রিয়াকরণ"],
            data_types=["personal_info", "contact_info"],
            purpose="SERVICE_DELIVERY",
            duration_days=730,
            version="1.0",
        ),
    },
}


class I18nService:
    def __init__(self):
        self.terms = CONSENT_TERMS
        self.templates = CONSENT_TEMPLATES

    def get_term(
        self, term_id: str, language: Language = Language.ENGLISH
    ) -> Optional[ConsentTerm]:
        return self.terms.get(term_id)

    def get_term_translation(self, term_id: str, language: Language = Language.ENGLISH) -> str:
        term = self.terms.get(term_id)
        if term:
            return term.translations.get(language.value, term.translations.get("en", term_id))
        return term_id

    def get_term_description(self, term_id: str, language: Language = Language.ENGLISH) -> str:
        term = self.terms.get(term_id)
        if term:
            return term.description.get(language.value, term.description.get("en", ""))
        return ""

    def get_template(
        self,
        template_id: str,
        language: Language = Language.ENGLISH,
    ) -> Optional[ConsentTemplate]:
        templates = self.templates.get(template_id)
        if templates:
            return templates.get(language, templates.get(Language.ENGLISH))
        return None

    def render_template(
        self,
        template_id: str,
        language: Language = Language.ENGLISH,
        fiduciary_name: str = "",
        data_types: Optional[List[str]] = None,
        duration_days: int = 365,
    ) -> Optional[str]:
        template = self.get_template(template_id, language)
        if not template:
            return None

        data_types_list = ""
        if data_types:
            data_types_list = "\n".join(
                f"- {self.get_term_translation(dt, language)}" for dt in data_types
            )

        return template.full_text.format(
            fiduciary_name=fiduciary_name,
            data_types_list=data_types_list,
            duration_days=duration_days,
        )

    def get_supported_languages(self) -> List[Dict[str, str]]:
        return [{"code": lang.value, "name": lang.name.title()} for lang in Language]

    def get_available_templates(self) -> List[str]:
        return list(self.templates.keys())


i18n_service = I18nService()
