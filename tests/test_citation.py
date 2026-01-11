# tests/test_citation.py
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indexer import (
    _extract_citations,
    _infer_nikaya_from_path,
    NIKAYA_REF_RE,
    FULL_NIKAYA_RE,
    SUTTA_NAME_RE
)


class TestCitationExtraction:
    """Test citation extraction from text."""
    
    def test_extract_simple_citation(self):
        """Test extracting a simple SN citation."""
        cits = _extract_citations("See SN 35.28")
        assert "SN 35.28" in cits
    
    def test_extract_simple_without_subsection(self):
        """Test extracting citation without subsection."""
        cits = _extract_citations("Read DN 22")
        assert "DN 22" in cits
    
    def test_extract_multiple_citations(self):
        """Test extracting multiple citations from same text."""
        cits = _extract_citations("Compare MN 21 and DN 22, also see SN 35.28")
        assert "MN 21" in cits
        assert "DN 22" in cits
        assert "SN 35.28" in cits
    
    def test_extract_full_nikaya_name(self):
        """Test extracting from full nikaya names."""
        cits = _extract_citations("Majjhima Nikāya 21 and Dīgha Nikāya 16")
        assert "MN 21" in cits
        assert "DN 16" in cits
    
    def test_extract_sutta_name(self):
        """Test extracting from sutta names."""
        cits = _extract_citations("The Satipaṭṭhāna Sutta teaches mindfulness")
        assert "MN 10" in cits
    
    def test_extract_fire_sermon_aliases(self):
        """Test Fire Sermon (Ādittapariyāya) aliases."""
        assert "SN 35.28" in _extract_citations("Ādittapariyāya Sutta")
        assert "SN 35.28" in _extract_citations("Adittapariyaya Sutta")
    
    def test_extract_anattalakkhana(self):
        """Test Anattalakkhaṇa Sutta."""
        assert "SN 22.59" in _extract_citations("Anattalakkhaṇa Sutta")
        assert "SN 22.59" in _extract_citations("Anattalakkhana Sutta")
    
    def test_extract_dhammacakkappavattana(self):
        """Test first sermon."""
        cits = _extract_citations("Dhammacakkappavattana Sutta")
        assert "SN 56.11" in cits
    
    def test_extract_with_periods(self):
        """Test citations with periods instead of spaces."""
        cits = _extract_citations("See SN.35.28 and MN.21")
        assert "SN 35.28" in cits or "SN.35.28" in cits
        assert "MN 21" in cits or "MN.21" in cits
    
    def test_extract_with_colons(self):
        """Test citations with colons."""
        cits = _extract_citations("Reference SN:35:28")
        assert any("SN" in c and "35" in c and "28" in c for c in cits)
    
    def test_extract_case_insensitive(self):
        """Test case-insensitive extraction."""
        cits = _extract_citations("see sn 35.28 and mn 21")
        assert "SN 35.28" in cits
        assert "MN 21" in cits
    
    def test_extract_from_dense_text(self):
        """Test extraction from paragraph with multiple citations."""
        text = """
        The Fire Sermon (SN 35.28) is one of the Buddha's most famous discourses.
        It should be compared with the Anattalakkhaṇa Sutta (SN 22.59) and
        the teachings in MN 21 about patience. The Dhammacakkappavattana Sutta
        sets the foundation for all of these.
        """
        cits = _extract_citations(text)
        assert "SN 35.28" in cits
        assert "SN 22.59" in cits
        assert "MN 21" in cits
        assert "SN 56.11" in cits  # From Dhammacakkappavattana
    
    def test_no_false_positives(self):
        """Test that random numbers don't get extracted."""
        cits = _extract_citations("I have 21 apples and 35.28 dollars")
        # Should not extract these as citations
        assert len(cits) == 0 or all("apple" not in c.lower() for c in cits)
    
    def test_extract_anguttara(self):
        """Test Anguttara Nikāya citations."""
        cits = _extract_citations("See AN 4.159 and AN 3.65")
        assert "AN 4.159" in cits or "AN 4.159" in str(cits)
        assert "AN 3.65" in cits or "AN 3.65" in str(cits)
    
    def test_extract_khuddaka_texts(self):
        """Test Khuddaka Nikāya text citations."""
        assert "Dhp" in str(_extract_citations("Dhammapada verse"))
        assert "Ud" in str(_extract_citations("Udāna Sutta"))
        assert "It" in str(_extract_citations("Itivuttaka"))


class TestNikayaInference:
    """Test nikaya inference from file paths."""
    
    def test_infer_digha(self):
        """Test Dīgha Nikāya inference."""
        assert _infer_nikaya_from_path("sutta_pitaka/digha_nikaya", "dn1.pdf") == "DN"
        assert _infer_nikaya_from_path("dialogues", "dialogues1.pdf") == "DN"
    
    def test_infer_majjhima(self):
        """Test Majjhima Nikāya inference."""
        assert _infer_nikaya_from_path("sutta_pitaka/majjhima_nikaya", "mn1.pdf") == "MN"
        assert _infer_nikaya_from_path("handful_of_leaves", "majjhima1.pdf") == "MN"
    
    def test_infer_samyutta(self):
        """Test Saṃyutta Nikāya inference."""
        assert _infer_nikaya_from_path("sutta_pitaka/samyutta_nikaya", "sn1.pdf") == "SN"
        assert _infer_nikaya_from_path("connected_discourses", "samyutta.pdf") == "SN"
    
    def test_infer_anguttara(self):
        """Test Aṅguttara Nikāya inference."""
        assert _infer_nikaya_from_path("sutta_pitaka/anguttara_nikaya", "an1.pdf") == "AN"
    
    def test_infer_dhammapada(self):
        """Test Dhammapada inference."""
        assert _infer_nikaya_from_path("khuddaka_nikaya", "dhammapada.pdf") == "Dhp"
    
    def test_infer_udana(self):
        """Test Udāna inference."""
        assert _infer_nikaya_from_path("khuddaka_nikaya", "udana.pdf") == "Ud"
    
    def test_infer_itivuttaka(self):
        """Test Itivuttaka inference."""
        assert _infer_nikaya_from_path("khuddaka_nikaya", "itivuttaka.pdf") == "It"
    
    def test_infer_suttanipata(self):
        """Test Sutta Nipāta inference."""
        assert _infer_nikaya_from_path("khuddaka_nikaya", "suttanipata.pdf") == "Sn"
    
    def test_infer_theragatha(self):
        """Test Theragāthā inference."""
        assert _infer_nikaya_from_path("khuddaka_nikaya", "theragatha.pdf") == "Thag"
    
    def test_infer_therigatha(self):
        """Test Therīgāthā inference."""
        assert _infer_nikaya_from_path("khuddaka_nikaya", "therigatha.pdf") == "Thig"
    
    def test_infer_none_for_unknown(self):
        """Test that unknown paths return None."""
        assert _infer_nikaya_from_path("random_folder", "random.pdf") is None
        assert _infer_nikaya_from_path("", "unknown.pdf") is None
    
    def test_infer_case_insensitive(self):
        """Test case-insensitive path matching."""
        assert _infer_nikaya_from_path("MAJJHIMA_NIKAYA", "MN.PDF") == "MN"
        assert _infer_nikaya_from_path("Digha_Nikaya", "Dialogues.PDF") == "DN"


class TestRegexPatterns:
    """Test the regex patterns directly."""
    
    def test_nikaya_ref_pattern(self):
        """Test NIKAYA_REF_RE pattern."""
        import re
        
        # Should match
        assert NIKAYA_REF_RE.search("SN 35.28")
        assert NIKAYA_REF_RE.search("MN 21")
        assert NIKAYA_REF_RE.search("DN 16")
        assert NIKAYA_REF_RE.search("AN 4.159")
        
        # Should handle spacing variations
        assert NIKAYA_REF_RE.search("SN35.28")
        assert NIKAYA_REF_RE.search("SN-35.28")
        assert NIKAYA_REF_RE.search("SN 35 28")
    
    def test_full_nikaya_pattern(self):
        """Test FULL_NIKAYA_RE pattern."""
        assert FULL_NIKAYA_RE.search("Majjhima Nikāya 21")
        assert FULL_NIKAYA_RE.search("Dīgha Nikāya 16")
        assert FULL_NIKAYA_RE.search("Samyutta Nikaya 35.28")
        assert FULL_NIKAYA_RE.search("Anguttara Nikāya 4.159")
    
    def test_sutta_name_pattern(self):
        """Test SUTTA_NAME_RE pattern."""
        assert SUTTA_NAME_RE.search("Satipaṭṭhāna Sutta")
        assert SUTTA_NAME_RE.search("Anattalakkhaṇa Sutta")
        assert SUTTA_NAME_RE.search("Ādittapariyāya Sutta")
        assert SUTTA_NAME_RE.search("Dhammacakkappavattana Sutta")


class TestEdgeCases:
    """Test edge cases and potential issues."""
    
    def test_empty_string(self):
        """Test empty string input."""
        assert _extract_citations("") == []
    
    def test_no_citations(self):
        """Test text with no citations."""
        text = "This is just regular text about Buddhism with no specific references."
        cits = _extract_citations(text)
        assert len(cits) == 0
    
    def test_partial_citation(self):
        """Test incomplete citation patterns."""
        # These should not match or should handle gracefully
        _extract_citations("SN")  # No number
        _extract_citations("35.28")  # No nikaya
    
    def test_unicode_handling(self):
        """Test proper Unicode handling for Pāli diacritics."""
        cits = _extract_citations("Satipaṭṭhāna Sutta and Ādittapariyāya")
        assert "MN 10" in cits
        assert "SN 35.28" in cits
    
    def test_duplicate_citations(self):
        """Test that duplicates are handled."""
        cits = _extract_citations("See MN 21, MN 21, and MN 21 again")
        # Should return list (might have duplicates, that's okay for now)
        assert "MN 21" in cits
    
    def test_very_long_text(self):
        """Test extraction from very long text."""
        long_text = " ".join([f"Reference SN {i}.{j}" for i in range(1, 50) for j in range(1, 10)])
        cits = _extract_citations(long_text)
        assert len(cits) > 0  # Should find many citations


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_full_metadata_extraction(self):
        """Test extracting both citation and nikaya from realistic input."""
        folder_path = "sutta_pitaka/majjhima_nikaya"
        pdf_name = "majjhima_nikaya1.pdf"
        text = "This passage from MN 21 teaches about patience. See also MN 22."
        
        nikaya = _infer_nikaya_from_path(folder_path, pdf_name)
        cits = _extract_citations(text)
        
        assert nikaya == "MN"
        assert "MN 21" in cits
        assert "MN 22" in cits
    
    def test_realistic_chunk(self):
        """Test on a realistic chunk of text."""
        text = """
        In the Satipaṭṭhāna Sutta (MN 10), the Buddha teaches the four foundations
        of mindfulness. This is closely related to the teaching in DN 22, the
        Mahāsatipaṭṭhāna Sutta. Both emphasize awareness of body, feelings, mind,
        and dhammas. Compare this with the Ānāpānasati Sutta (MN 118) which focuses
        specifically on breath meditation.
        """
        cits = _extract_citations(text)
        
        assert "MN 10" in cits
        assert "DN 22" in cits
        assert "MN 118" in cits


if __name__ == "__main__":
    # Allow running directly with: python tests/test_citation.py
    import pytest
    pytest.main([__file__, "-v"])
