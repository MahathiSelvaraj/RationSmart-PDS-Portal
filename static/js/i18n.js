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

    // Additional Login & General Form Terms
    'Username': 'பயனர் பெயர்',
    'Password': 'கடவுச்சொல்',
    'Sign In': 'உள்நுழைக',
    'Remember me': 'என்னை நினைவில் கொள்',
    'Dealer': 'டீலர்',
    'Citizen': 'பொதுமக்கள்',
    'Administrator': 'நிர்வாகி',
    'Role': 'பங்கு',

    // Status Values
    'Active': 'செயலில்',
    'Inactive': 'செயலற்றது',
    'Completed': 'நிறைவடைந்தது',
    'Pending': 'நிலுவையில்',
    'Resolved': 'தீர்க்கப்பட்டது',
    'Rejected': 'நிராகரிக்கப்பட்டது',

    // Receipt & Verification Labels
    'Disbursed Date & Time': 'வழங்கப்பட்ட தேதி & நேரம்',
    'Beneficiary Details': 'பயனாளி விவரங்கள்',
    'Identity Verification:': 'அடையாள சரிபார்ப்பு:',
    'Commodities Distributed': 'வழங்கப்பட்ட உணவுப் பொருட்கள்',
    'Grand Total Amount:': 'செலுத்த வேண்டிய மொத்த தொகை:',
    'Print Digital Memo': 'ரசீது அச்சிடுக',
    'Biometric Auth:': 'கைரேகை சரிபார்ப்பு:',
    'Cardholder Name:': 'கார்டுதாரர் பெயர்:',
    'Scheme Category:': 'திட்டப் பிரிவு:',

    // Commodities
    'Rice (NFSA Grade A)': 'அரிசி (தரம் A)',
    'Wheat (Fortified Atta)': 'கோதுமை (செறிவூட்டப்பட்டது)',
    'Refined Sugar': 'சர்க்கரை',
    'Subsidized Kerosene': 'மண்ணெண்ணெய்',
    'Tur Dal / Pulses': 'துவரம் பருப்பு',
    'FREE': 'இலவசம்',
    'FREE (₹0.00)': 'இலவசம் (₹0.00)',
    'Per Person': 'ஒருவருக்கு',
    'Per Card': 'அட்டைக்கு',
    // Stock Status & Shop Badges
    'Adequate': 'போதுமானது',
    'Insufficient Data': 'போதிய தரவு இல்லை',
    'Low Stock Alert': 'குறைந்த இருப்பு எச்சரிக்கை',
    'Low Stock': 'குறைந்த இருப்பு',
    'Current Inventory': 'தற்போதைய இருப்பு',
    'Shop Stock Status': 'கடை இருப்பு நிலை',
    'Offline Cache': 'ஆஃப்லைன் தற்காலிக சேமிப்பு',
    'Threshold': 'வரம்பு',
    'Threshold:': 'வரம்பு:',

    // Replenishment Requests Page
    'Stock Replenishment Requests': 'இருப்பு நிரப்புதல் கோரிக்கைகள்',
    'Stock Replenishment': 'இருப்பு நிரப்புதல்',
    'Received request replenishment': 'இருப்பு கோரிக்கை பெறப்பட்டது',
    'Request Replenishment': 'இருப்பு கோருக',
    'Submit New Stock Request': 'புதிய இருப்பு கோரிக்கை சமர்ப்பிக்கவும்',
    'Submit Replenishment Indent': 'இருப்பு கோரிக்கையைச் சமர்ப்பி',
    'Submit Request': 'கோரிக்கையைச் சமர்ப்பி',
    'Select Commodity': 'உணவுப் பொருளைத் தேர்ந்தெடுக்கவும்',
    'Select Commodity *': 'உணவுப் பொருளைத் தேர்ந்தெடுக்கவும் *',
    '-- Choose Commodity --': '-- உணவுப் பொருளைத் தேர்ந்தெடுக்கவும் --',
    'Current Shop Stock': 'தற்போதைய கடை இருப்பு',
    'Alert Threshold': 'எச்சரிக்கை வரம்பு',
    'Requested Quantity': 'கோரப்பட்ட அளவு',
    'Requested Quantity *': 'கோரப்பட்ட அளவு *',
    'e.g. 500.0': 'எ.கா. 500.0',
    'kg/L': 'கிலோ / லிட்டர்',
    'Enter positive quantity required to sustain entitlement distribution.': 'ஒதுக்கீட்டு விநியோகத்தை பராமரிக்க தேவையான அளவை உள்ளிடவும்.',
    'Justification / Reason for Indent': 'கோரிக்கைக்கான காரணம் / விளக்கம்',
    'Justification / Reason for Indent *': 'கோரிக்கைக்கான காரணம் / விளக்கம் *',
    'Explain the requirement (e.g. Stock below threshold, upcoming holiday footfall surge, high customer density in ward)...': 'தேவையை விளக்குங்கள் (எ.கா. வரம்பிற்கு கீழ் இருப்பு, விடுமுறை நாட்களில் கூடுதல் வருகை, வார்டில் அதிக நுகர்வோர் எண்ணிக்கை)...',
    'Minimum 5 characters. Justification will be reviewed by District Supply Office.': 'குறைந்தபட்சம் 5 எழுத்துக்கள். இந்த விளக்கம் மாவட்ட வழங்கல் அலுவலகத்தால் மதிப்பாய்வு செய்யப்படும்.',
    'Indent History & Decision Trail': 'கோரிக்கை வரலாறு & முடிவு விவரங்கள்',
    'All Statuses': 'அனைத்து நிலைகளும்',
    'No Replenishment Requests Found': 'இருப்பு கோரிக்கைகள் எதுவும் காணப்படவில்லை',
    'Use the form on the left to submit your first stock indent.': 'உங்கள் முதல் இருப்பு கோரிக்கையைச் சமர்ப்பிக்க இடதுபுறத்தில் உள்ள படிவத்தைப் பயன்படுத்தவும்.',
    'Submit stock indent requests, monitor District DSO approvals, and safely record physical delivery receipts.': 'இருப்பு கோரிக்கைகளைச் சமர்ப்பிக்கவும், மாவட்ட DSO ஒப்புதல்களைக் கண்காணிக்கவும், டெலிவரி ரசீதுகளைப் பதிவு செய்யவும்.',

    // Navigation & Table Actions
    'My Stock Monitor': 'இருப்பு கண்காணிப்பு',
    'Open POS Counter': 'பில்லிங் கவுண்டரைத் திற',
    'Total Indents': 'மொத்தக் கோரிக்கைகள்',
    'All-Time Requests': 'எல்லாக் காலக் கோரிக்கைகள்',
    'Pending Review': 'பரிசீலனையில் உள்ளவை',
    'Awaiting Admin Decision': 'நிர்வாக முடிவுக்கு காத்திருக்கிறது',
    'Approved / In-Transit': 'ஒப்புதல் அளிக்கப்பட்டது / வழியில்',
    'Ready for Stock Receipt': 'சரக்கு வரவு பெற தயார்',
    'Fulfilled Stocks': 'நிறைவேற்றப்பட்ட சரக்குகள்',
    'Received & Updated': 'பெறப்பட்டு புதுப்பிக்கப்பட்டது',
    'Request ID': 'கோரிக்கை எண்',
    'Requested': 'கோரப்பட்டது',
    'Details / Reason': 'விவரங்கள் / காரணம்',
    'Actions': 'செயல்கள்',
    'Cancel': 'ரத்து செய்',
    'Record Receipt': 'இருப்பு வரவு பதிவு',
    'Stock Added': 'சரக்கு சேர்க்கப்பட்டது',
    'Closed': 'முடிக்கப்பட்டது',
    'Cancelled': 'ரத்து செய்யப்பட்டது',
    'Snapshot:': 'இருப்பு நிலை:',
    'DSO Remark:': 'DSO குறிப்பு:',
    'Record Physical Stock Receipt': 'நேரடி சரக்கு வரவைப் பதிவு செய்க',
    'Request Identifier': 'கோரிக்கை எண்',
    'Approved Quantity': 'ஒப்புதல் அளிக்கப்பட்ட அளவு',
    'Actual Received Quantity': 'உண்மையில் பெறப்பட்ட அளவு',
    'Delivery Challan / Invoice No.': 'டெலிவரி சலான் / இன்வாய்ஸ் எண்',
    'Confirm Stock Receipt & Update Shop Ledger': 'சரக்கு வரவை உறுதிசெய்து இருப்பைப் புதுப்பி',
    'Confirm Stock Receipt': 'சரக்கு வரவை உறுதி செய்',

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
        const dict = targetLang === 'ta' ? PDS_I18N_DICT : PDS_I18N_REVERSE;

        // 1. Inputs and Textareas with placeholder
        document.querySelectorAll('input[placeholder], textarea[placeholder]').forEach(el => {
            const ph = el.getAttribute('placeholder');
            if (ph && dict[ph.trim()]) {
                el.setAttribute('placeholder', dict[ph.trim()]);
            }
        });

        // 2. Select option texts
        document.querySelectorAll('select option').forEach(opt => {
            const txt = opt.textContent.trim();
            if (txt && dict[txt]) {
                opt.textContent = dict[txt];
            }
        });

        // 3. Card search specific fallback
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
