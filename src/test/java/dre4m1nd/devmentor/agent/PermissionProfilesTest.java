package dre4m1nd.devmentor.agent;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.agentscope.core.permission.PermissionContextState;
import io.agentscope.core.permission.PermissionMode;
import org.junit.jupiter.api.Test;

class PermissionProfilesTest {

    @Test
    void interactiveAllowsReadsButAsksBeforeWrites() {
        PermissionContextState state = PermissionProfiles.of("interactive");
        // ACCEPT_EDITS = 只读自动放行、其余询问；DEFAULT 会让 read_file 也弹确认，不可用。
        assertThat(state.getMode()).isEqualTo(PermissionMode.ACCEPT_EDITS);
        assertThat(state.getAskRules()).containsKeys("execute", "write_file", "edit_file");
        assertThat(state.isTrivial()).isFalse();
    }

    @Test
    void readOnlyMapsToExplore() {
        assertThat(PermissionProfiles.of("read-only").getMode()).isEqualTo(PermissionMode.EXPLORE);
        assertThat(PermissionProfiles.of("readonly").getMode()).isEqualTo(PermissionMode.EXPLORE);
        assertThat(PermissionProfiles.of("READ_ONLY").getMode()).isEqualTo(PermissionMode.EXPLORE);
    }

    @Test
    void fullMapsToBypass() {
        assertThat(PermissionProfiles.of("full").getMode()).isEqualTo(PermissionMode.BYPASS);
        assertThat(PermissionProfiles.of("bypass").getMode()).isEqualTo(PermissionMode.BYPASS);
    }

    @Test
    void blankFallsBackToInteractive() {
        assertThat(PermissionProfiles.of(null).getMode()).isEqualTo(PermissionMode.ACCEPT_EDITS);
        assertThat(PermissionProfiles.of("  ").getMode()).isEqualTo(PermissionMode.ACCEPT_EDITS);
    }

    @Test
    void unknownProfileIsRejected() {
        assertThatThrownBy(() -> PermissionProfiles.of("yolo"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("interactive");
    }
}
