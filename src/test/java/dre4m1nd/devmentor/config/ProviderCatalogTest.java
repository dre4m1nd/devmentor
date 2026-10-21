package dre4m1nd.devmentor.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class ProviderCatalogTest {

    @Test
    void firstProviderIsTheFreeOne() {
        // 第一项必须是免费可用路径，否则"开箱即用"的承诺就不成立。
        assertThat(ProviderCatalog.PROVIDERS.get(0).label()).contains("OpenRouter");
        assertThat(ProviderCatalog.PROVIDERS.get(0).defaultModel()).endsWith(":free");
    }

    @Test
    void idsAreUniqueAndContiguous() {
        for (int i = 0; i < ProviderCatalog.PROVIDERS.size(); i++) {
            assertThat(ProviderCatalog.PROVIDERS.get(i).id()).isEqualTo(i + 1);
        }
    }

    @Test
    void everyProviderHasModelAndProviderPrefix() {
        for (ProviderCatalog.Provider p : ProviderCatalog.PROVIDERS) {
            assertThat(p.provider()).isNotBlank();
            assertThat(p.defaultModel()).isNotBlank();
            assertThat(p.provider()).doesNotContain(":");
        }
    }

    @Test
    void byIdFindsProviderAndReturnsNullForUnknown() {
        assertThat(ProviderCatalog.byId(1).provider()).isEqualTo("openai");
        assertThat(ProviderCatalog.byId(999)).isNull();
    }

    @Test
    void ollamaNeedsNoKey() {
        ProviderCatalog.Provider ollama = ProviderCatalog.byProvider("ollama");
        assertThat(ollama).isNotNull();
        assertThat(ProviderCatalog.requiresKey(ollama)).isFalse();
    }

    @Test
    void cloudProvidersRequireKey() {
        for (ProviderCatalog.Provider p : ProviderCatalog.PROVIDERS) {
            if (!"ollama".equals(p.provider())) {
                assertThat(ProviderCatalog.requiresKey(p))
                        .as("provider %s 应当需要 Key", p.provider())
                        .isTrue();
            }
        }
    }

    @Test
    void menuListsEveryProvider() {
        String menu = ProviderCatalog.menu();
        for (ProviderCatalog.Provider p : ProviderCatalog.PROVIDERS) {
            assertThat(menu).contains(p.label());
        }
    }
}
