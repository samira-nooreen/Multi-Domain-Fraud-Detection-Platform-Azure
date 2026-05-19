"""
Brand Abuse Detection Prediction
"""
import joblib
import pandas as pd
import numpy as np
import re
from collections import Counter
import os

class BrandAbuseDetector:
    def __init__(self, model_path='brand_abuse_model.pkl'):
        self.model_path = model_path
        self.model = None
        self.feature_cols = None
        self.load_model()
        
    def load_model(self):
        try:
            if os.path.exists(self.model_path):
                data = joblib.load(self.model_path)
                if isinstance(data, dict) and 'model' in data:
                    self.model = data['model']
                    self.feature_cols = data.get('feature_cols', [])
                else:
                    self.model = data # Fallback for old models
            else:
                print(f"Model file {self.model_path} not found.")
        except Exception as e:
            print(f"Error loading model: {e}")
            self.model = None

    def _get_domain_features(self, url):
        """Extract domain-related features"""
        try:
            # Extract domain
            domain = url.split('//')[-1].split('/')[0].split(':')[0]
            
            # Domain length
            domain_length = len(domain)
            
            # Number of dots
            dot_count = domain.count('.')
            
            # Number of hyphens
            hyphen_count = domain.count('-')
            
            # Number of digits
            digit_count = sum(1 for c in domain if c.isdigit())
            
            # Number of special characters
            special_char_count = sum(1 for c in domain if not c.isalnum() and c != '.' and c != '-')
            
            # Entropy (randomness)
            if domain:
                counts = Counter(domain)
                length = len(domain)
                entropy = -sum((count/length) * np.log2(count/length) for count in counts.values())
            else:
                entropy = 0
                
            # Suspicious TLDs
            suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.ru', '.cn']
            suspicious_tld = 1 if any(domain.endswith(tld) for tld in suspicious_tlds) else 0
            
            # Subdomain count
            subdomain_count = max(0, domain.count('.') - 1)
                
            return {
                'domain_length': domain_length,
                'dot_count': dot_count,
                'hyphen_count': hyphen_count,
                'digit_count': digit_count,
                'special_char_count': special_char_count,
                'entropy': entropy,
                'suspicious_tld': suspicious_tld,
                'subdomain_count': subdomain_count
            }
        except:
            return {
                'domain_length': 0,
                'dot_count': 0,
                'hyphen_count': 0,
                'digit_count': 0,
                'special_char_count': 0,
                'entropy': 0,
                'suspicious_tld': 0,
                'subdomain_count': 0
            }

    def _check_brand_similarity(self, text, brand_keywords):
        """Check similarity to brand keywords"""
        if not text or not brand_keywords:
            return 0
            
        text_lower = text.lower()
        max_similarity = 0
        
        for brand in brand_keywords:
            brand_lower = brand.lower()
            # Exact match
            if brand_lower in text_lower:
                max_similarity = max(max_similarity, 1.0)
            # Partial match
            elif any(word in text_lower for word in brand_lower.split()):
                max_similarity = max(max_similarity, 0.7)
            # Fuzzy match (typos, substitutions)
            elif self._fuzzy_match(brand_lower, text_lower):
                max_similarity = max(max_similarity, 0.5)
                
        return max_similarity

    def _fuzzy_match(self, brand, text):
        """Simple fuzzy matching for typos"""
        # Check for common typo patterns
        if self._levenshtein_distance(brand, text) <= 2:
            return True
        # Check for character substitutions (e.g., 0 for o, 1 for l)
        if self._substitution_match(brand, text):
            return True
        return False

    def _levenshtein_distance(self, s1, s2):
        """Calculate Levenshtein distance between two strings"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _substitution_match(self, brand, text):
        """Check for common character substitutions"""
        substitutions = {'0': 'o', '1': 'l', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b'}
        substituted_brand = ''.join(substitutions.get(c, c) for c in brand)
        return substituted_brand in text
        
    def _is_official_domain(self, url, brand_keywords):
        """Check if the domain is likely an official brand domain"""
        # Extract domain
        domain = url.split('//')[-1].split('/')[0].split(':')[0].lower()
        
        # Check if it's a known official domain
        official_domains = ['nike.com', 'adidas.com', 'apple.com', 'amazon.com', 'google.com', 
                          'microsoft.com', 'samsung.com', 'sony.com']
        
        # Check if domain matches official domains
        if any(official in domain for official in official_domains):
            return True
            
        # Check if domain contains brand name and is likely official
        for brand in brand_keywords:
            brand_clean = brand.lower().replace(' ', '')
            if brand_clean in domain and not any(suspicious in domain 
                                               for suspicious in ['fake', 'copy', ' replica']):
                return True
                
        return False
        
    def _is_legitimate_brand_page(self, url, brand_keywords):
        """Check if this appears to be a legitimate brand page"""
        # Extract domain and path
        domain = url.split('//')[-1].split('/')[0].split(':')[0].lower()
        path = '/' + '/'.join(url.split('//')[-1].split('/')[1:]) if len(url.split('//')[-1].split('/')) > 1 else ''
        
        # Known legitimate patterns
        legitimate_patterns = [
            'product', 'products', 'shop', 'store', 'buy', 
            'official', 'authentic', 'original'
        ]
        
        # If it's on an official domain and has legitimate patterns, it's likely legitimate
        if self._is_official_domain(url, brand_keywords) and \
           any(pattern in path.lower() for pattern in legitimate_patterns):
            return True
            
        return False
        
    def _is_legitimate_promotion(self, url, brand_keywords):
        """Check if promotional language is in a legitimate context"""
        # If it's on an official domain, promotional language might be legitimate
        if self._is_official_domain(url, brand_keywords):
            return True
        return False
        
    def _get_social_selling_features(self, data):
        """Extract features specific to social selling platforms"""
        brand_keywords = data.get('brand_keywords', [])
        seller_name = data.get('seller_name', '').lower()
        listing_title = data.get('listing_title', '').lower()
        description = data.get('description', '').lower()
        
        features = {}
        
        # Seller name features
        features['has_brand_in_name'] = 1 if any(brand.lower() in seller_name for brand in brand_keywords) else 0
        features['brand_fuzzy_match'] = self._check_brand_similarity(seller_name, brand_keywords)
        features['has_official'] = 1 if 'official' in seller_name else 0
        
        # Discount tokens
        discount_tokens = ['%', 'off', 'discount', 'deal', 'clearance', 'sale']
        features['discount_tokens_count'] = sum(1 for token in discount_tokens if token in seller_name or token in listing_title or token in description)
        
        # Special characters ratio (for typosquatting)
        total_chars = len(seller_name)
        special_chars = sum(1 for c in seller_name if not c.isalnum() and c != ' ')
        features['special_chars_ratio'] = special_chars / total_chars if total_chars > 0 else 0
        
        # Name length
        features['name_length'] = len(seller_name)
        
        # Scam indicators
        replica_words = ['replica', 'copy', 'fake', 'same as original', 'best copy', 'oem']
        features['has_replica_words'] = 1 if any(word in description or word in listing_title for word in replica_words) else 0
        
        free_giveaway_words = ['free', 'giveaway', 'win', 'gift']
        features['has_free_giveaway'] = 1 if any(word in description or word in listing_title for word in free_giveaway_words) else 0
        
        features['has_same_as_original'] = 1 if 'same as original' in description or 'same as original' in listing_title else 0
        
        # Brand presence in content
        features['has_brand_in_title'] = 1 if any(brand.lower() in listing_title for brand in brand_keywords) else 0
        features['has_brand_in_description'] = 1 if any(brand.lower() in description for brand in brand_keywords) else 0
        
        return features
        
    def _get_social_indicators(self, data, features):
        """Get specific indicators for social selling platform abuse"""
        indicators = []
        
        # Seller name indicators
        if features.get('has_brand_in_name', 0) > 0:
            indicators.append("brand-in-name")
        if features.get('has_official', 0) > 0:
            indicators.append("'official' in seller name")
        if features.get('brand_fuzzy_match', 0) > 0.5:
            indicators.append("fuzzy brand match in name")
            
        # Discount indicators
        if features.get('discount_tokens_count', 0) > 0:
            indicators.append("discount tokens detected")
            
        # Scam indicators
        if features.get('has_replica_words', 0) > 0:
            indicators.append("replica-wording: 'same as original'")
        if features.get('has_free_giveaway', 0) > 0:
            indicators.append("free/giveaway language detected")
        if features.get('has_same_as_original', 0) > 0:
            indicators.append("'same as original' phrase detected")
            
        # Content indicators
        if features.get('has_brand_in_title', 0) > 0:
            indicators.append("brand in listing title")
        if features.get('has_brand_in_description', 0) > 0:
            indicators.append("brand in description")
            
        # Image indicators
        if data.get('images_uploaded', 0) > 0:
            indicators.append(f"{data.get('images_uploaded')} images uploaded for analysis")
            
        return indicators
        
    def _mock_predict_social_selling(self, data):
        """Heuristic fallback prediction for social selling platforms"""
        brand_keywords = data.get('brand_keywords', [])
        # Handle case where brand_keywords is a string (comma-separated)
        if isinstance(brand_keywords, str):
            brand_keywords = [kw.strip() for kw in brand_keywords.split(',') if kw.strip()]
        
        seller_name = data.get('seller_name', '').lower()
        listing_title = data.get('listing_title', '').lower()
        description = data.get('description', '').lower()
        url = data.get('url', '').lower()
        
        # Early exit for legitimate domains
        if self._is_official_domain(url, brand_keywords):
            return {
                'is_brand_abuse': False,
                'abuse_probability': 0.1,
                'risk_level': 'LOW',
                'confidence': 0.95,
                'indicators': ['Legitimate official domain detected']
            }
        
        score = 0
        indicators = []
        
        # Enhanced risk scoring logic for social selling
        
        # 1. Brand Misuse in Seller Name (+25)
        if any(brand.lower() in seller_name for brand in brand_keywords):
            score += 25
            indicators.append("Brand in seller name")
        
        # 2. "Official" Claim Outside Real Domain (+25)
        if 'official' in seller_name and not self._is_official_domain(url, brand_keywords):
            score += 25
            indicators.append("\"official\" used outside real domain")
        
        # 3. Scam Phrases (+30)
        scam_phrases = ['replica', 'copy', 'fake', 'same as original', 'best copy', 'oem', '70% off', '75% off']
        if any(phrase in description or phrase in listing_title for phrase in scam_phrases):
            score += 30
            indicators.append("Scam phrases detected")
        
        # 4. Discount Abuse (+20)
        discount_patterns = ['%', 'off', 'discount', 'deal', 'clearance']
        if any(pattern in seller_name or pattern in listing_title or pattern in description for pattern in discount_patterns):
            score += 20
            indicators.append("Excessive discount language")
        
        # 5. Suspicious Domain (+30)
        suspicious_domains = ['facebook.com/marketplace', 'instagram.com']
        if any(domain in url for domain in suspicious_domains) and not self._is_legitimate_brand_page(url, brand_keywords):
            score += 30
            indicators.append("Suspicious social selling platform")
        
        # 6. Counterfeit Indicators (+40)
        counterfeit_indicators = ['same as original', 'best copy', 'factory copy', 'oem']
        if any(indicator in description or indicator in listing_title for indicator in counterfeit_indicators):
            score += 40
            indicators.append("Counterfeit product indicators")
        
        # 7. Fake Reseller Patterns (+30)
        reseller_patterns = ['outlet', 'store', 'shop']
        if any(pattern in seller_name for pattern in reseller_patterns) and not self._is_official_domain(url, brand_keywords):
            score += 30
            indicators.append("Fake reseller pattern detected")
        
        # Normalize score to 0-100 range
        normalized_score = min(100, score)
        prob = normalized_score / 100.0
        
        # Determine risk level based on score
        if normalized_score >= 85:
            risk_level = 'CRITICAL'
        elif normalized_score >= 60:
            risk_level = 'HIGH'
        elif normalized_score >= 30:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
            
        return {
            'is_brand_abuse': bool(normalized_score >= 30),
            'abuse_probability': float(prob),
            'risk_level': risk_level,
            'confidence': 0.9 if normalized_score >= 30 else 0.8,
            'indicators': indicators
        }

    def predict(self, data):
        """
        Predict brand abuse for social selling platforms (Facebook, Instagram)
        
        Args:
            data: Dictionary containing:
                - url: Seller profile link
                - brand_keywords: List of brand keywords
                - seller_name: Seller/page name
                - listing_title: Listing title (optional)
                - description: Post description (optional)
                - images_uploaded: Number of images uploaded (optional)
        """
        if self.model is None:
            return self._mock_predict_social_selling(data)
            
        try:
            url = data.get('url', '')
            brand_keywords = data.get('brand_keywords', [])
            # Handle case where brand_keywords is a string (comma-separated)
            if isinstance(brand_keywords, str):
                brand_keywords = [kw.strip() for kw in brand_keywords.split(',') if kw.strip()]
            seller_name = data.get('seller_name', '')
            listing_title = data.get('listing_title', '')
            description = data.get('description', '')
            images_uploaded = data.get('images_uploaded', 0)
            
            # Extract domain features for analysis
            domain_features = self._get_domain_features(url)
            
            # Extract social selling specific features
            social_features = self._get_social_selling_features(data)
            
            # Combine all features
            features = {
                **domain_features,
                **social_features,
                'has_brand_keywords': 1 if brand_keywords else 0,
                'images_uploaded': images_uploaded
            }
            
            # Ensure all expected features are present
            expected_features = [
                'domain_length', 'dot_count', 'hyphen_count', 'digit_count', 
                'special_char_count', 'entropy', 'suspicious_tld', 'subdomain_count',
                'has_brand_in_name', 'brand_fuzzy_match', 'has_official',
                'discount_tokens_count', 'special_chars_ratio', 'name_length',
                'has_replica_words', 'has_free_giveaway', 'has_same_as_original',
                'has_brand_in_title', 'has_brand_in_description',
                'has_brand_keywords', 'images_uploaded'
            ]
            
            # Fill in missing features with default values
            for feature in expected_features:
                if feature not in features:
                    features[feature] = 0
            
            # Create DataFrame with correct column order
            if self.feature_cols:
                # Ensure all required columns are present
                feature_dict = {}
                for col in self.feature_cols:
                    feature_dict[col] = features.get(col, 0)
                df = pd.DataFrame([feature_dict])
            else:
                # Fallback if feature_cols not saved
                df = pd.DataFrame([features])
            
            # Predict using trained model
            prob = self.model.predict_proba(df)[0][1]
            
            # Determine risk level based on probability
            if prob > 0.85:
                risk_level = 'CRITICAL'
            elif prob > 0.6:
                risk_level = 'HIGH'
            elif prob > 0.3:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            return {
                'is_brand_abuse': bool(prob > 0.4),
                'abuse_probability': float(prob),
                'risk_level': risk_level,
                'confidence': 0.95,  # Placeholder confidence
                'indicators': self._get_social_indicators(data, features),
            }
        except Exception as e:
            print(f"Prediction error: {e}")
            return self._mock_predict_social_selling(data)
            
    def _get_indicators(self, url, brand_keywords, domain_features, url_brand_similarity):
        """Get specific indicators of brand abuse"""
        indicators = []
        
        # Domain-based indicators
        if domain_features['domain_length'] > 30:
            indicators.append("Suspiciously long domain name")
        if domain_features['hyphen_count'] > 3:
            indicators.append("Excessive hyphens in domain")
        if domain_features['digit_count'] > 3:
            indicators.append("Unusual digits in domain")
        if domain_features['entropy'] > 4.0:
            indicators.append("High randomness in domain")
            
        # Brand similarity indicators
        if url_brand_similarity > 0.8:
            indicators.append("Exact brand match detected")
        elif url_brand_similarity > 0.5:
            indicators.append("Strong brand similarity detected")
        elif url_brand_similarity > 0.3:
            indicators.append("Possible brand impersonation")
            
        # Suspicious TLDs
        suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.ru', '.cn']
        for tld in suspicious_tlds:
            if url.endswith(tld):
                indicators.append(f"Suspicious top-level domain: {tld}")
                
        # Additional indicators for brand abuse patterns
        # Only flag social media domains if they're not legitimate brand pages
        if 'social.com' in url and not self._is_legitimate_brand_page(url, brand_keywords):
            indicators.append("Suspicious social media domain")
            
        # Only flag "official" misuse if it's not on an official domain
        if 'official' in url and not self._is_official_domain(url, brand_keywords):
            indicators.append("\"official\" used outside real domain")
            
        # Flag promotional keywords in suspicious contexts
        if ('free' in url or 'gift' in url or 'giveaway' in url) and not self._is_legitimate_promotion(url, brand_keywords):
            indicators.append("Promotional keywords in URL")
            
        # Only flag mimic patterns for non-official domains
        if '-' in url and any(brand in url for brand in brand_keywords) and not self._is_official_domain(url, brand_keywords):
            indicators.append("Mimic URL pattern detected")
                
        return indicators
            
    def _mock_predict(self, data):
        """Heuristic fallback prediction with improved risk scoring (general brand abuse)"""
        url = data.get('url', '').lower()
        content_text = data.get('content_text', '').lower()
        brand_keywords = data.get('brand_keywords', [])
        # Handle case where brand_keywords is a string (comma-separated)
        if isinstance(brand_keywords, str):
            brand_keywords = [kw.strip() for kw in brand_keywords.split(',') if kw.strip()]
        
        # Early exit for legitimate domains
        if self._is_official_domain(url, brand_keywords):
            return {
                'is_brand_abuse': False,
                'abuse_probability': 0.1,
                'risk_level': 'LOW',
                'confidence': 0.95,
                'indicators': ['Legitimate official domain detected']
            }
        
        score = 0
        indicators = []
        
        # Enhanced risk scoring logic
        
        # 1. Keyword Abuse
        # Exact brand match
        for brand in brand_keywords:
            if brand.lower() in url:
                score += 20
                indicators.append("Exact brand match detected")
                break
        
        # Brand keyword in URL
        for brand in brand_keywords:
            if brand.lower() in url:
                score += 25
                indicators.append("Brand keyword in URL")
                break
        
        # "official" used outside real domain
        if 'official' in url and not self._is_official_domain(url, brand_keywords):
            score += 25
            indicators.append("\"official\" used outside real domain")
        
        # 2. Scam Indicators
        # "free gift", "giveaway", "win"
        scam_keywords = ['free', 'gift', 'giveaway', 'win', 'reward']
        if any(keyword in content_text for keyword in scam_keywords) and not self._is_legitimate_promotion(url, brand_keywords):
            score += 30
            indicators.append("Scam keywords detected (free, gift, giveaway, win)")
        
        # "Click the link"
        if 'click' in content_text and ('link' in content_text or 'claim' in content_text):
            score += 20
            indicators.append("\"Click the link\" pattern detected")
        
        # Suspicious domain (non-brand)
        suspicious_domains = ['social.com', 'freegift', 'fanpage', 'community']
        if any(domain in url for domain in suspicious_domains) and not self._is_legitimate_brand_page(url, brand_keywords):
            score += 30
            indicators.append("Suspicious domain pattern detected")
        
        # 3. Impersonation Patterns
        # Account/page pretending to be brand
        impersonation_patterns = ['official', 'fanpage', 'community', 'support']
        if any(pattern in url for pattern in impersonation_patterns) and not self._is_official_domain(url, brand_keywords):
            score += 40
            indicators.append("Impersonation pattern detected")
        
        # Mimic URL pattern
        if '-' in url and any(brand in url for brand in brand_keywords) and not self._is_official_domain(url, brand_keywords):
            score += 30
            indicators.append("Mimic URL pattern detected")
        
        # Normalize score to 0-100 range
        normalized_score = min(100, score)
        prob = normalized_score / 100.0
        
        # Determine risk level based on score
        if normalized_score >= 80:
            risk_level = 'CRITICAL'
        elif normalized_score >= 60:
            risk_level = 'HIGH'
        elif normalized_score >= 40:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
            
        return {
            'is_brand_abuse': bool(normalized_score >= 40),
            'abuse_probability': float(prob),
            'risk_level': risk_level,
            'confidence': 0.9 if normalized_score >= 40 else 0.8,
            'indicators': indicators
        }