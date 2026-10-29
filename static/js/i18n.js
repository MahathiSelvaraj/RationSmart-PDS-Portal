/**
 * RationSmart - Bilingual Localization Engine (தமிழ் ⇄ English)
 * Real-time instant language switcher with localStorage persistence.
 * Synchronizes with PDSVoiceAssistant for seamless speech in the active language.
 */

const PDS_I18N_DICT = {
    // Top Bar & Identity
    'Government of Tamil Nadu': 'தமிழ்நாடு அரசு',
    'Department of Food and Civil Supplies': 'உணவு மற்றும் நுகர்வோர் பாதுகாப்புத்துறை',
    'Public Distribution System • Grain Allocation Tracking Portal': 'பொது விநியோகத் திட்டம் • உணவு தானிய ஒதுக்கீடு கண்காணிப்பு தளம்',
    'Public Distribution System': 'பொது விநியோகத் திட்டம்',
    'National Food Security Portal': 'தேசிய உணவுப் பாதுகாப்புத் தளம்',

    // Navigation Menu
    'Home': 'முகப்பு',
    'My Shop Billing': 'கடை பில்லிங் (POS)',
    'My Stock': 'எனது இருப்பு',
    'Stock Indents': 'இருப்பு கோரிக்கைகள்',
    'My Transactions': 'பரிவர்த்தனைகள்',
    'Shop Complaints': 'கடை புகார்கள்',
    'Offline Sales': 'ஆஃப்லைன் விற்பனை',
    'My Ration Portal': 'எனது ரேஷன் போர்டல்',
    'Raise Complaint': 'புகார் பதிவு',
    'Raise a Complaint': 'புகார் பதிவு செய்க',
    'Transactions': 'பரிவர்த்தனைகள்',
    'Transaction Alerts': 'பரிவர்த்தனை எச்சரிக்கைகள்',
    'Reports': 'அறிக்கைகள்',
    'Complaints': 'புகார்கள்',
    'Audit Logs': 'தணிக்கை பதிவுகள்',
    'Dashboard': 'டாஷ்போர்டு',
    'Sign In / Login': 'உள்நுழை',
    'Sign Out': 'வெளியேறு',
    'Logout': 'வெளியேறு',
    'Portal Navigation Menu': 'போர்டல் வழிசெலுத்தல் மெனு',

    // Status Pills & Buttons
    'Online': 'ஆன்லைன்',
    'Offline': 'ஆஃப்லைன்',
    'Offline (Simulation)': 'ஆஃப்லைன் (சோதனை)',
    'Install': 'நிறுவுக (Install)',
    'Sync Now': 'இப்போது ஒத்திசை',
    'Retry Connection': 'மீண்டும் இணை',
    'Exit Simulation': 'வெளியேறு (Online)',
    'Exit Simulation / Go Online': 'வெளியேறு / ஆன்லைன் செல்',
    'Simulate Offline': 'ஆஃப்லைன் சோதனை',
    'Pending Sync': 'ஒத்திசைவு நிலுவையில்',
    'Confirmed Synced': 'ஒத்திசைக்கப்பட்டது',
    'Total Local Records': 'மொத்த உள்ளூர் பதிவுகள்',
    'Last Successful Sync': 'கடைசி ஒத்திசைவு',
    'All Local Records': 'அனைத்து உள்ளூர் பதிவுகள்',
    'Refresh': 'புதுப்பி',

    // POS Counter & Steps
    'Step 1: Authenticate Beneficiary / Search Ration Card': 'படி 1: பயனாளி சரிபார்ப்பு / ரேஷன் கார்டு தேடல்',
    'Lookup': 'தேடுக',
    'Step 2: Grain Disbursal & Biometric Recording': 'படி 2: தானிய விநியோகம் & பதிவு',
    'Step 2: Grain Disbursal & Biometric Recording (Offline Mode)': 'படி 2: தானிய விநியோகம் & பதிவு (ஆஃப்லைன் முறை)',
    'Citizen Authentication Method': 'பயனாளி சரிபார்ப்பு முறை',
    'Payment Mode': 'பணம் செலுத்தும் முறை',
    'Cash / Direct Subsidy': 'ரொக்கம் / மானிய விலை',
    'Direct Benefit Transfer (DBT Zero Cash)': 'நேரடி மானியம் (கட்டணமில்லை)',
    'UPI / Bharat QR': 'UPI / பாரத் QR',
    'Confirm & Generate Digital e-Receipt': 'உறுதி செய்து ரசீது உருவாக்கு',
    'Save Offline Sale & Queue for Sync': 'ஆஃப்லைன் விற்பனையை சேமிக்கவும்',
    'Record Next Customer': 'அடுத்த வாடிக்கையாளர்',
    'View Offline Register': 'ஆஃப்லைன் பதிவேடு',
    'Offline POS Terminal Active:': 'ஆஃப்லைன் POS முனையம் செயல்படுகிறது:',
    'Card Not Found in Offline Cache:': 'ஆஃப்லைன் பதிவேட்டில் அட்டை இல்லை:',
    'Total Subsidized Bill Amount:': 'மொத்த மானிய பில் தொகை:',
    'Total Bill Amount:': 'மொத்த பில் தொகை:',
    'Grand Total Amount Paid:': 'செலுத்தப்பட்ட மொத்த தொகை:',

    // Table Headers
    'Commodity': 'உணவுப் பொருள்',
    'Unit Price': 'விலை',
    'Monthly Entitlement': 'மாத ஒதுக்கீடு',
    'Already Received': 'பெற்றவை',
    'Already Lifted': 'பெற்றவை',
    'Remaining Quota': 'மீதமுள்ள ஒதுக்கீடு',
    'Remaining': 'மீதமுள்ளவை',
    'Disburse Qty': 'வழங்கும் அளவு',
    'Subtotal': 'மொத்தம்',
    'Subtotal (₹)': 'மொத்தம் (₹)',
    'Rate (₹)': 'விலை (₹)',
    'Quantity': 'அளவு',
    'Allocation Basis': 'ஒதுக்கீட்டு அடிப்படை',
    'Status / Action': 'நிலை / செயல்',
    'Status': 'நிலை',
    'Action': 'செயல்',
    'Receipt': 'ரசீது',
    'Date & Time': 'தேதி & நேரம்',
    'Bill Number': 'பில் எண்',
    'Bill Number:': 'பில் எண்:',
    'Idempotency Key (Client ID)': 'தனித்துவ விசை (Client ID)',
    'Beneficiary Card': 'பயனாளி அட்டை',
    'Grains Distributed': 'வழங்கப்பட்ட தானியங்கள்',
    'Amount': 'தொகை',
    'Print Digital e-Receipt': 'ரசீது அச்சிடுக',
    'Back': 'பின்செல்',
    'Fair Price Shop:': 'நியாய விலைக் கடை:',
    'Licensed Dealer:': 'உரிமம் பெற்ற டீலர்:',
    'Beneficiary:': 'பயனாளி:',
    'Category:': 'அட்டை வகை:',
    'Members:': 'உறுப்பினர்கள்:',
    'Member(s)': 'உறுப்பினர்கள்',
    'Card No:': 'அட்டை எண்:',

    // Citizen Dashboard & Quota
    'Cardholder Details': 'கார்டுதாரர் விவரங்கள்',
    'Family Members Registered': 'குடும்ப உறுப்பினர்கள்',
    'No family members registered.': 'குடும்ப உறுப்பினர்கள் விவரமில்லை.',
    'Assigned Fair Price Shop': 'ஒதுக்கப்பட்ட நியாய விலைக் கடை',
    'Not Assigned': 'ஒதுக்கப்படவில்லை',
    'Public Grievance Redressal & Support': 'பொதுமக்கள் குறைதீர்ப்பு & ஆதரவு',
    'Shop QR Code': 'கடை QR குறியீடு',
    'Fair Price Shop Complaint QR': 'நியாய விலைக் கடை புகார் QR',
    'Download QR Image': 'QR படம் பதிவிறக்கு',
    'Close': 'மூடு',

    // Commodities
    'Rice (NFSA Grade A)': 'அரிசி (தரம் A)',
    'Wheat (Fortified Atta)': 'கோதுமை (செறிவூட்டப்பட்டது)',
    'Refined Sugar': 'சர்க்கரை',
    'Subsidized Kerosene': 'மண்ணெண்ணெய்',
    'Tur Dal / Pulses': 'துவரம் பருப்பு',
    'FREE': 'இலவசம்',
    'FREE (₹0.00)': 'இலவசம் (₹0.00)',
    'Per Person': 'ஒருவருக்கு',
    'Per Card': 'அட்டைக்கு'
};

// Reverse Dictionary (Tamil -> English)
const PDS_I18N_REVERSE = {};
for (const [en, ta] of Object.entries(PDS_I18N_DICT)) {
    PDS_I18N_REVERSE[ta] = en;
}

class PDSI18n {
    constructor() {
        this.lang = localStorage.getItem('pds_portal_lang') || 'en'; // 'en' | 'ta'
        this.init();
    }

    init() {
        // Apply on initial DOM load
        document.addEventListener('DOMContentLoaded', () => {
            this.updateToggleUI();
            if (this.lang === 'ta') {
                this.translatePageToTamil();
            }
        });
    }

    getLanguage() {
        return this.lang;
    }

    setLanguage(newLang) {
        this.lang = newLang === 'ta' ? 'ta' : 'en';
        localStorage.setItem('pds_portal_lang', this.lang);
        
        // Also update voice engine language
        if (window.pdsVoice) {
            window.pdsVoice.setLanguage(this.lang);
        }

        this.updateToggleUI();

        if (this.lang === 'ta') {
            this.translatePageToTamil();
        } else {
            this.translatePageToEnglish();
        }
    }

    toggleLanguage() {
        this.setLanguage(this.lang === 'en' ? 'ta' : 'en');
    }

    updateToggleUI() {
        const label = document.getElementById('pdsCurrentLangLabel');
        if (label) {
            label.innerText = this.lang === 'en' ? 'தமிழ்' : 'English';
        }
    }

    translatePageToTamil() {
        this.walkAndTranslate(PDS_I18N_DICT);
        this.translateInputsAndPlaceholders('ta');
    }

    translatePageToEnglish() {
        this.walkAndTranslate(PDS_I18N_REVERSE);
        this.translateInputsAndPlaceholders('en');
    }

    walkAndTranslate(dictionary) {
        // Exclude script, style, and code elements
        const ignoreTags = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE', 'INPUT', 'TEXTAREA']);

        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: (node) => {
                    if (!node.parentElement) return NodeFilter.FILTER_REJECT;
                    if (ignoreTags.has(node.parentElement.tagName)) return NodeFilter.FILTER_REJECT;
                    // Ignore elements with no-translate class
                    if (node.parentElement.closest('.no-translate')) return NodeFilter.FILTER_REJECT;
                    return NodeFilter.FILTER_ACCEPT;
                }
            }
        );

        let node;
        while ((node = walker.nextNode())) {
            const trimmed = node.nodeValue.trim();
            if (trimmed && dictionary[trimmed]) {
                node.nodeValue = node.nodeValue.replace(trimmed, dictionary[trimmed]);
            }
        }
    }

    translateInputsAndPlaceholders(targetLang) {
        const searchInput = document.getElementById('posCardSearchInput');
        if (searchInput) {
            if (targetLang === 'ta') {
                searchInput.setAttribute('placeholder', 'ரேஷன் அட்டை எண் அல்லது கடைசி 4 ஆதார் எண் உள்ளிடவும்...');
            } else {
                searchInput.setAttribute('placeholder', 'Scan / Enter Ration Card No. or Aadhaar Last 4...');
            }
        }
    }

    applyCurrentLanguage() {
        if (this.lang === 'ta') {
            this.translatePageToTamil();
        }
    }
}

// Global Singleton Instance
window.pdsI18n = new PDSI18n();
