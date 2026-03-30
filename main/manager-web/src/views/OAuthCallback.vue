<template>
  <div class="oauth-callback">
    <div class="callback-box">
      <template v-if="loading">
        <i class="el-icon-loading" style="font-size: 40px; color: #5778ff"></i>
        <p style="margin-top: 20px; color: #666">{{ $t('socialLogin.processing') }}</p>
      </template>
      <template v-else-if="error">
        <i class="el-icon-circle-close" style="font-size: 40px; color: #f56c6c"></i>
        <p style="margin-top: 20px; color: #f56c6c">{{ errorMsg }}</p>
        <el-button type="primary" style="margin-top: 20px" @click="goToLogin">
          {{ $t('socialLogin.backToLogin') }}
        </el-button>
      </template>
    </div>
  </div>
</template>

<script>
import Api from "@/apis/api";
import { goToPage, showSuccess, showDanger } from "@/utils";

export default {
  name: "OAuthCallback",
  data() {
    return {
      loading: true,
      error: false,
      errorMsg: "",
    };
  },
  mounted() {
    this.handleCallback();
  },
  methods: {
    handleCallback() {
      const code = this.$route.query.code;
      const state = this.$route.query.state;
      const provider = this.$route.query.provider || localStorage.getItem("oauth_provider");

      if (!code || !provider) {
        this.error = true;
        this.errorMsg = this.$t('socialLogin.invalidCallback');
        this.loading = false;
        return;
      }

      Api.user.socialLoginCallback(
        provider,
        { code, state },
        ({ data }) => {
          this.loading = false;
          localStorage.removeItem("oauth_provider");
          showSuccess(this.$t('login.loginSuccess'));
          this.$store.commit("setToken", JSON.stringify(data.data));
          goToPage("/home");
        },
        (err) => {
          this.loading = false;
          this.error = true;
          this.errorMsg = (err.data && err.data.msg) || this.$t('socialLogin.loginFailed');
          localStorage.removeItem("oauth_provider");
        }
      );
    },
    goToLogin() {
      goToPage("/login");
    },
  },
};
</script>

<style scoped>
.oauth-callback {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f5f7fa;
}

.callback-box {
  text-align: center;
  padding: 60px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}
</style>
