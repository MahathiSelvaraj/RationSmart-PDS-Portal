/**
 * RationSmart - Rural Accessibility & Voice Assistance Engine
 * Uses W3C Web Speech API (speechSynthesis)
 * 100% Offline-capable, zero external API keys.
 * Supports Tamil (ta-IN) & Indian English (en-IN).
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
        this.voices = this.synth.getVoices();
    }

    getVoice(langCode) {
        if (!this.voices || this.voices.length === 0) {
            this.initVoices();
        }

        if (langCode === 'ta') {
            // Find Tamil voice
            const tamilVoice = this.voices.find(v => 
                v.lang === 'ta-IN' || 
                v.lang === 'ta_IN' || 
                v.lang.toLowerCase().startsWith('ta') ||
                v.name.toLowerCase().includes('tamil')
            );
            if (tamilVoice) return tamilVoice;

            // Fallback to Indian English or English if Tamil voice is not installed on OS
            return this.voices.find(v => v.lang === 'en-IN' || v.lang.startsWith('en')) || null;
        } else {
            // Find English (Indian English preferred)
            return this.voices.find(v => v.lang === 'en-IN') || 
                   this.voices.find(v => v.lang.startsWith('en')) || null;
        }
    }

    setLanguage(newLang) {
        this.lang = newLang === 'en' ? 'en' : 'ta';
        localStorage.setItem('pds_voice_lang', this.lang);
        this.updateLanguageUI();
    }

    toggleLanguage() {
        this.setLanguage(this.lang === 'ta' ? 'en' : 'ta');
    }

    updateLanguageUI() {
        const langBadges = document.querySelectorAll('.pds-voice-lang-badge');
        langBadges.forEach(badge => {
            badge.innerText = this.lang === 'ta' ? 'தமிழ்' : 'English';
        });
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

    speak(textTamil, textEnglish, triggerButton = null) {
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

        const hasTamilVoice = this.voices.some(v => v.lang.startsWith('ta') || v.name.toLowerCase().includes('tamil'));
        const chosenVoice = this.getVoice(this.lang);
        
        let textToSpeak = '';
        let utteranceLang = 'en-IN';

        if (this.lang === 'ta' && hasTamilVoice) {
            textToSpeak = textTamil;
            utteranceLang = 'ta-IN';
        } else if (this.lang === 'ta' && !hasTamilVoice) {
            // If Tamil voice is missing on OS, fall back to English with a gentle notice
            textToSpeak = textEnglish;
            utteranceLang = 'en-IN';
        } else {
            textToSpeak = textEnglish;
            utteranceLang = 'en-IN';
        }

        const utterance = new SpeechSynthesisUtterance(textToSpeak);
        utterance.lang = utteranceLang;
        if (chosenVoice) utterance.voice = chosenVoice;
        utterance.rate = 0.92; // Slightly calm pace for clarity
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
        const tamilItems = quotaItems.map(item => {
            const comm = translateCommodityToTamil(item.name || item.commodity_name);
            const unit = translateUnitToTamil(item.unit);
            const qty = item.remaining_qty !== undefined ? item.remaining_qty : item.entitled_qty;
            return `${comm} ${qty} ${unit}`;
        }).join(', ');

        const englishItems = quotaItems.map(item => {
            const qty = item.remaining_qty !== undefined ? item.remaining_qty : item.entitled_qty;
            return `${qty} ${item.unit} of ${item.name || item.commodity_name}`;
        }).join(', ');

        const textTamil = `வணக்கம் ${cardHolder} அவர்களே. உங்கள் ${cardType} ரேஷன் அட்டைக்கான இந்த மாத ஒதுக்கீடு விவரம்: ${tamilItems}. நியாய விலைக் கடையில் பெற்றுக்கொள்ளலாம். நன்றி.`;
        const textEnglish = `Hello ${cardHolder}. Your monthly quota for ${cardType} ration card is: ${englishItems}. Thank you.`;

        this.speak(textTamil, textEnglish, triggerButton);
    }

    // High-Level Helper: Speak Sale / Bill Receipt
    speakSaleReceipt(billNumber, cardHolder, items, totalAmount, triggerButton = null) {
        const tamilItems = items.map(item => {
            const comm = translateCommodityToTamil(item.name || item.commodity_name);
            const unit = translateUnitToTamil(item.unit);
            return `${comm} ${item.quantity} ${unit}`;
        }).join(', ');

        const englishItems = items.map(item => {
            return `${item.quantity} ${item.unit} of ${item.name || item.commodity_name}`;
        }).join(', ');

        const amtVal = parseFloat(totalAmount) || 0;
        const amtTamil = amtVal === 0 ? 'இலவசம்' : `ரூபாய் ${amtVal.toFixed(0)}`;
        const amtEnglish = amtVal === 0 ? 'Zero Rupees (Free Scheme)' : `${amtVal.toFixed(2)} Rupees`;

        const textTamil = `வணக்கம் ${cardHolder} அவர்களே. உங்கள் பில் எண் ${billNumber}. வழங்கப்பட்ட பொருட்கள்: ${tamilItems}. மொத்த பில் தொகை: ${amtTamil}. பொருட்கள் வெற்றிகரமாக வழங்கப்பட்டது. நன்றி.`;
        const textEnglish = `Hello ${cardHolder}. Bill number ${billNumber}. Disbursed items: ${englishItems}. Total bill amount: ${amtEnglish}. Transaction completed successfully. Thank you.`;

        this.speak(textTamil, textEnglish, triggerButton);
    }
}

// Global Translation Helpers
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

// Global Singleton Instance
window.pdsVoice = new PDSVoiceAssistant();
