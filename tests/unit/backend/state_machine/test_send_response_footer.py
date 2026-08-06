################################################################################
# Unit tests for the identity footer appended to ALL outgoing messages.
################################################################################

from state_machine.processing.send_response import build_identity_footer


class TestIdentityFooter:
    def test_footer_authenticated_with_profile(self):
        footer = build_identity_footer(
            authenticated="true",
            profile={"full_name": "Santiago Garcia", "nickname": "Santi"},
        )
        assert footer == "\n\n🔐 Autenticado: Sí ✅ | 👤 Santiago Garcia (Santi)"

    def test_footer_incognito_never_shows_name_even_with_profile(self):
        footer = build_identity_footer(
            authenticated="false",
            profile={"full_name": "Santiago Garcia", "nickname": "Santi"},
        )
        assert footer == "\n\n🔐 Autenticado: No | 👤 Incógnito 🕵️"
        assert "Santiago" not in footer

    def test_footer_incognito_without_profile(self):
        footer = build_identity_footer(authenticated="false", profile={})
        assert footer == "\n\n🔐 Autenticado: No | 👤 Incógnito 🕵️"

    def test_footer_handles_none_profile(self):
        footer = build_identity_footer(authenticated="true", profile=None)
        assert "Autenticado" in footer
