/**
 * RationSmart - Rural Accessibility & Voice Assistance Engine
 * Uses W3C Web Speech API (speechSynthesis)
 * 100% Offline-capable, zero external API keys.
 * 
 * DUAL-LAYER TAMIL SYNTHESIS:
 * Layer 1: Native Tamil Voice (ta-IN / Valluvar / Pallavi / Google Tamil) using pure Tamil script.
 * Layer 2: Phonetic Tamil (Tanglish) using Indian English voice (Heera / Ravi / en-IN),
 *          so even without a Tamil voice installed, the user hears TAMIL words, never English!
 */

class PDSVoiceAssistant {
    constructor() {
        this.synth = ('speechSynthesis' in window) ? window.speechSynthesis : null;
        this.isSpeaking = false;
        this.currentButton = null;
        this.lang = localStorage.getItem('pds_voice_lang') || 'ta'; // 'ta' for Tamil, 'en' for English
        this.voices = [];

        if (this.synth) {
            this.initVoices();
            if (this.synth.onvoiceschanged !== undefined) {
                this.synth.onvoiceschanged = () => this.initVoices();
            }
        }
    }

    initVoices() {
        if (!this.synth) return;
        this.voices = this.synth.getVoices() || [];
    }

    findTamilVoice() {
        if (!this.voices || this.voices.length === 0) {
            this.initVoices();
        }
        return this.voices.find(v => 
            v.lang.toLowerCase() === 'ta-in' || 
            v.lang.toLowerCase() === 'ta_in' || 
            v.lang.toLowerCase().startsWith('ta') ||
            v.name.toLowerCase().includes('tamil') ||
            v.name.toLowerCase().includes('valluvar') ||
            v.name.toLowerCase().includes('pallavi')
        ) || null;
    }

    findIndianEnglishVoice() {
        if (!this.voices || this.voices.length === 0) {
            this.initVoices();
        }
        return this.voices.find(v => 
            v.lang.toLowerCase() === 'en-in' || 
            v.lang.toLowerCase() === 'en_in' ||
            v.name.toLowerCase().includes('india') ||
            v.name.toLowerCase().includes('heera') ||
            v.name.toLowerCase().includes('ravi')
        ) || this.voices.find(v => v.lang.startsWith('en')) || null;
    }

    setLanguage(newLang) {
        this.lang = newLang === 'en' ? 'en' : 'ta';
        localStorage.setItem('pds_voice_lang', this.lang);
    }

    stop() {
        if (this.synth) {
            this.synth.cancel();
        }
        this.resetButton();
        this.isSpeaking = false;
    }

    resetButton() {
        if (this.currentButton) {
            const originalHtml = this.currentButton.getAttribute('data-original-html');
            if (originalHtml) {
                this.currentButton.innerHTML = originalHtml;
            }
            this.currentButton.classList.remove('btn-danger');
            this.currentButton = null;
        }
    }

    speakPayload({ textTamil, textTanglish, textEnglish, triggerButton = null }) {
        if (!this.synth) {
            alert('Your device or browser does not support Voice Speech Synthesis.');
            return;
        }

        // If currently speaking, stop it
        if (this.isSpeaking) {
            this.stop();
            if (triggerButton && triggerButton === this.currentButton) {
                return; // User clicked stop
            }
        }

        // Always refresh voices before playing
        this.initVoices();

        const tamilVoice = this.findTamilVoice();
        const indianVoice = this.findIndianEnglishVoice();

        let textToSpeak = '';
        let utteranceLang = 'ta-IN';
        let selectedVoice = null;

        if (this.lang === 'en') {
            // User explicitly requested English
            textToSpeak = textEnglish;
            utteranceLang = 'en-IN';
            selectedVoice = indianVoice;
        } else {
            // User wants Tamil (DEFAULT)
            if (tamilVoice) {
                // Native Tamil voice is installed (e.g. Edge Natural Valluvar/Pallavi or Chrome Tamil)
                textToSpeak = textTamil;
                utteranceLang = 'ta-IN';
                selectedVoice = tamilVoice;
            } else {
                // No native Tamil voice installed on OS -> Speak Phonetic Tamil (Tanglish)
                // Using Indian English voice (Heera/Ravi) so it sounds like Tamil spoken aloud!
                textToSpeak = textTanglish;
                utteranceLang = 'en-IN';
                selectedVoice = indianVoice;
            }
        }

        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        utterance.lang = utteranceLang;
        if (selectedVoice) {
            utterance.voice = selectedVoice;
        }
        utterance.rate = 0.88; // Calm and clear pace
        utterance.pitch = 1.0;

        if (triggerButton) {
            this.currentButton = triggerButton;
            if (!triggerButton.getAttribute('data-original-html')) {
                triggerButton.setAttribute('data-original-html', triggerButton.innerHTML);
            }
            triggerButton.innerHTML = '<i class="bi bi-stop-circle-fill me-1 text-danger"></i> நிறுத்து (Stop)';
        }

        this.isSpeaking = true;

        utterance.onend = () => {
            this.isSpeaking = false;
            this.resetButton();
        };

        utterance.onerror = (e) => {
            console.warn('[Voice Assistant] Playback error or cancelled:', e);
            this.isSpeaking = false;
            this.resetButton();
        };

        this.synth.speak(utterance);
    }

    // High-Level Helper: Speak Beneficiary Quota
    speakBeneficiaryQuota(cardHolder, cardType, quotaItems, triggerButton = null) {
        // 1. Pure Tamil Text (for native Tamil TTS)
        const tamilItems = quotaItems.map(item => {
            const comm = translateCommodityToTamil(item.name || item.commodity_name);
            const unit = translateUnitToTamil(item.unit);
            const qty = item.remaining_qty !== undefined ? item.remaining_qty : item.entitled_qty;
            return `${comm} ${qty} ${unit}`;
        }).join(', ');

        const textTamil = `வணக்கம் ${cardHolder} அவர்களே. உங்கள் ${cardType} ரேஷன் அட்டைக்கான இந்த மாத ஒதுக்கீடு விவரம்: ${tamilItems}. நியாய விலைக் கடையில் பெற்றுக்கொள்ளலாம். நன்றி.`;

        // 2. Tanglish Phonetic Text (for Indian/English voices to speak Tamil phonetically)
        const tanglishItems = quotaItems.map(item => {
            const comm = translateCommodityToTanglish(item.name || item.commodity_name);
            const unit = translateUnitToTanglish(item.unit);
            const qty = item.remaining_qty !== undefined ? item.remaining_qty : item.entitled_qty;
            return `${comm} ${qty} ${unit}`;
        }).join(', ');

        const textTanglish = `Vanakkam ${cardHolder} avargale. Ungal ${cardType} ration cardukku intha maatha othukkeedu vivaram: ${tanglishItems}. Niyaya vilai kadaiyil petrukkollalaam. Nandri.`;

        // 3. English Text
        const englishItems = quotaItems.map(item => {
            const qty = item.remaining_qty !== undefined ? item.remaining_qty : item.entitled_qty;
            return `${qty} ${item.unit} of ${item.name || item.commodity_name}`;
        }).join(', ');

        const textEnglish = `Hello ${cardHolder}. Your monthly quota for ${cardType} ration card is: ${englishItems}. Thank you.`;

        this.speakPayload({
            textTamil,
            textTanglish,
            textEnglish,
            triggerButton
        });
    }

    // High-Level Helper: Speak Sale / Bill Receipt
    speakSaleReceipt(billNumber, cardHolder, items, totalAmount, triggerButton = null) {
        const amtVal = parseFloat(totalAmount) || 0;

        // 1. Pure Tamil Text
        const tamilItems = items.map(item => {
            const comm = translateCommodityToTamil(item.name || item.commodity_name);
            const unit = translateUnitToTamil(item.unit);
            return `${comm} ${item.quantity} ${unit}`;
        }).join(', ');

        const amtTamil = amtVal === 0 ? 'இலவசம்' : `ரூபாய் ${amtVal.toFixed(0)}`;
        const textTamil = `வணக்கம் ${cardHolder} அவர்களே. உங்கள் பில் எண் ${billNumber}. வழங்கப்பட்ட பொருட்கள்: ${tamilItems}. மொத்த பில் தொகை: ${amtTamil}. பொருட்கள் வெற்றிகரமாக வழங்கப்பட்டது. நன்றி.`;

        // 2. Tanglish Phonetic Text
        const tanglishItems = items.map(item => {
            const comm = translateCommodityToTanglish(item.name || item.commodity_name);
            const unit = translateUnitToTanglish(item.unit);
            return `${comm} ${item.quantity} ${unit}`;
        }).join(', ');

        const amtTanglish = amtVal === 0 ? 'Ilavasam' : `${amtVal.toFixed(0)} Roobai`;
        const textTanglish = `Vanakkam ${cardHolder} avargale. Ungal bill en ${billNumber}. Vazhangappatta porutkal: ${tanglishItems}. Mottha bill thogai: ${amtTanglish}. Porutkal vetrigaramaaga vazhangappattathu. Nandri.`;

        // 3. English Text
        const englishItems = items.map(item => `${item.quantity} ${item.unit} of ${item.name || item.commodity_name}`).join(', ');
        const amtEnglish = amtVal === 0 ? 'Zero Rupees (Free Scheme)' : `${amtVal.toFixed(2)} Rupees`;
        const textEnglish = `Hello ${cardHolder}. Bill number ${billNumber}. Disbursed items: ${englishItems}. Total bill amount: ${amtEnglish}. Transaction completed successfully. Thank you.`;

        this.speakPayload({
            textTamil,
            textTanglish,
            textEnglish,
            triggerButton
        });
    }
}

// Global Translation Helpers (Pure Tamil)
function translateCommodityToTamil(name) {
    if (!name) return 'பொருள்';
    const n = name.toLowerCase();
    if (n.includes('rice')) return 'அரிசி';
    if (n.includes('wheat') || n.includes('atta')) return 'கோதுமை';
    if (n.includes('sugar')) return 'சர்க்கரை';
    if (n.includes('kerosene')) return 'மண்ணெண்ணெய்';
    if (n.includes('dal') || n.includes('pulse')) return 'துவரம் பருப்பு';
    if (n.includes('oil')) return 'பாமாயில்';
    return name;
}

function translateUnitToTamil(unit) {
    if (!unit) return '';
    const u = unit.toLowerCase();
    if (u.includes('kg')) return 'கிலோ';
    if (u.includes('liter') || u.includes('litre')) return 'லிட்டர்';
    return unit;
}

// Global Translation Helpers (Phonetic Tanglish for Indian English Voice)
function translateCommodityToTanglish(name) {
    if (!name) return 'porul';
    const n = name.toLowerCase();
    if (n.includes('rice')) return 'Arisi';
    if (n.includes('wheat') || n.includes('atta')) return 'Gothumai';
    if (n.includes('sugar')) return 'Sarkkarai';
    if (n.includes('kerosene')) return 'Mannenney';
    if (n.includes('dal') || n.includes('pulse')) return 'Thuvaram Paruppu';
    if (n.includes('oil')) return 'Paamayil';
    return name;
}

function translateUnitToTanglish(unit) {
    if (!unit) return '';
    const u = unit.toLowerCase();
    if (u.includes('kg')) return 'kilo';
    if (u.includes('liter') || u.includes('litre')) return 'liter';
    return unit;
}

// Global Singleton Instance
window.pdsVoice = new PDSVoiceAssistant();
