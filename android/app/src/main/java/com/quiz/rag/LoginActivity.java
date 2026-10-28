package com.quiz.rag;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.TextUtils;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.quiz.rag.db.DbHelper;
import com.quiz.rag.net.ApiClient;
import com.quiz.rag.util.PasswordToggle;

import java.util.HashMap;
import java.util.Map;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * Lab Exp 12: Login backed by SQLite and the real backend API.
 * The backend is the source of truth whenever it is reachable; SQLite is only
 * used as an offline fallback, never to fake a successful login.
 */
public class LoginActivity extends AppCompatActivity {

    private EditText etEmail, etPassword, etServerUrl;
    private Button btnLogin, btnGuest, btnSaveUrl;
    private TextView tvGoToRegister, tvServerStatus;
    private DbHelper dbHelper;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_login);

        dbHelper = new DbHelper(this);

        etEmail = findViewById(R.id.etLoginEmail);
        etPassword = findViewById(R.id.etLoginPassword);
        btnLogin = findViewById(R.id.btnLogin);
        btnGuest = findViewById(R.id.btnGuest);
        tvGoToRegister = findViewById(R.id.tvGoToRegister);
        etServerUrl = findViewById(R.id.etLoginServerUrl);
        btnSaveUrl = findViewById(R.id.btnLoginSaveUrl);
        tvServerStatus = findViewById(R.id.tvServerStatus);

        etServerUrl.setText(ApiClient.getSavedBaseUrl(this));
        PasswordToggle.attach(etPassword);

        btnLogin.setOnClickListener(v -> attemptLogin());
        btnGuest.setOnClickListener(v -> playAsGuest());
        btnSaveUrl.setOnClickListener(v -> {
            String url = etServerUrl.getText().toString().trim();
            if (!url.isEmpty()) {
                ApiClient.setSavedBaseUrl(this, url);
                etServerUrl.setText(ApiClient.getSavedBaseUrl(this));
            }
            checkServerReachable();
        });
        tvGoToRegister.setOnClickListener(v -> {
            startActivity(new Intent(LoginActivity.this, RegisterActivity.class));
        });

        checkServerReachable();
    }

    /** Pings /api/health so a bad server URL is visible before you try to sign in. */
    private void checkServerReachable() {
        tvServerStatus.setText("Checking connection...");
        tvServerStatus.setTextColor(getResources().getColor(R.color.text_muted));

        ApiClient.get(this).health().enqueue(new Callback<Map<String, Object>>() {
            @Override
            public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                if (response.isSuccessful()) {
                    tvServerStatus.setText("✓ Connected to server");
                    tvServerStatus.setTextColor(getResources().getColor(R.color.success));
                } else {
                    tvServerStatus.setText("Server responded with error " + response.code());
                    tvServerStatus.setTextColor(getResources().getColor(R.color.warning));
                }
            }

            @Override
            public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                tvServerStatus.setText("✗ Cannot reach server - check this URL");
                tvServerStatus.setTextColor(getResources().getColor(R.color.error));
            }
        });
    }

    private void attemptLogin() {
        String email = etEmail.getText().toString().trim();
        String password = etPassword.getText().toString().trim();

        if (TextUtils.isEmpty(email)) {
            etEmail.setError("Email is required");
            return;
        }
        if (TextUtils.isEmpty(password)) {
            etPassword.setError("Password is required");
            return;
        }

        Map<String, String> body = new HashMap<>();
        body.put("email", email);
        body.put("password", password);

        btnLogin.setEnabled(false);

        ApiClient.get(this).login(body).enqueue(new Callback<Map<String, Object>>() {
            @SuppressWarnings("unchecked")
            @Override
            public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                btnLogin.setEnabled(true);
                if (response.isSuccessful() && response.body() != null) {
                    String token = String.valueOf(response.body().get("access_token"));
                    Map<String, Object> user = (Map<String, Object>) response.body().get("user");
                    String username = user != null ? String.valueOf(user.get("username")) : email;
                    saveSessionAndProceed(username, email, token, false);
                    Toast.makeText(LoginActivity.this, "Welcome back, " + username + "!", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(LoginActivity.this, "Invalid email or password", Toast.LENGTH_LONG).show();
                }
            }

            @Override
            public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                btnLogin.setEnabled(true);
                // Server unreachable: allow a genuine offline fallback via local SQLite only.
                if (dbHelper.checkLogin(email, password)) {
                    saveSessionAndProceed(email, email, "offline_token", false);
                    Toast.makeText(LoginActivity.this, "Server unreachable - signed in with offline data", Toast.LENGTH_LONG).show();
                } else {
                    Toast.makeText(LoginActivity.this, "Cannot reach server: " + t.getMessage(), Toast.LENGTH_LONG).show();
                }
            }
        });
    }

    private void playAsGuest() {
        btnGuest.setEnabled(false);
        ApiClient.get(this).guestLogin().enqueue(new Callback<Map<String, Object>>() {
            @SuppressWarnings("unchecked")
            @Override
            public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                btnGuest.setEnabled(true);
                if (response.isSuccessful() && response.body() != null) {
                    String token = String.valueOf(response.body().get("access_token"));
                    Map<String, Object> user = (Map<String, Object>) response.body().get("user");
                    String guestName = user != null ? String.valueOf(user.get("username")) : "Guest";
                    saveSessionAndProceed(guestName, null, token, true);
                    Toast.makeText(LoginActivity.this, "Playing as " + guestName, Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(LoginActivity.this, "Could not start guest session", Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                btnGuest.setEnabled(true);
                Toast.makeText(LoginActivity.this, "Cannot reach server: " + t.getMessage(), Toast.LENGTH_LONG).show();
            }
        });
    }

    private void saveSessionAndProceed(String username, String email, String token, boolean isGuest) {
        SharedPreferences prefs = getSharedPreferences("rag_prefs", MODE_PRIVATE);
        prefs.edit()
                .putString("username", username)
                .putString("email", email != null ? email : username + "@guest.local")
                .putString("token", token)
                .putBoolean("is_guest", isGuest)
                .apply();

        startActivity(new Intent(LoginActivity.this, MainActivity.class));
        finish();
    }
}
