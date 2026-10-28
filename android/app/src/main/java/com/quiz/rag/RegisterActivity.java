package com.quiz.rag;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.text.TextUtils;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.RadioButton;
import android.widget.RadioGroup;
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

public class RegisterActivity extends AppCompatActivity {

    private EditText etUsername, etEmail, etPassword, etAddress, etAge;
    private RadioGroup rgGender;
    private RadioButton rbMale, rbFemale, rbOther;
    private ImageView ivAvatarPreview;
    private Button btnCycleAvatar, btnSubmitRegister;
    private TextView tvBackToLogin;

    private int currentAvatar = 1;
    private final int[] avatarDrawables = {
            R.drawable.ic_avatar_1,
            R.drawable.ic_avatar_2,
            R.drawable.ic_avatar_3,
            R.drawable.ic_avatar_4,
            R.drawable.ic_avatar_5
    };

    private DbHelper dbHelper;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_register);

        dbHelper = new DbHelper(this);

        etUsername = findViewById(R.id.etRegUsername);
        etEmail = findViewById(R.id.etRegEmail);
        etPassword = findViewById(R.id.etRegPassword);
        etAddress = findViewById(R.id.etRegAddress);
        etAge = findViewById(R.id.etRegAge);
        rgGender = findViewById(R.id.rgGender);
        rbMale = findViewById(R.id.rbMale);
        rbFemale = findViewById(R.id.rbFemale);
        rbOther = findViewById(R.id.rbOther);
        ivAvatarPreview = findViewById(R.id.ivAvatarPreview);
        btnCycleAvatar = findViewById(R.id.btnCycleAvatar);
        btnSubmitRegister = findViewById(R.id.btnSubmitRegister);
        tvBackToLogin = findViewById(R.id.tvBackToLogin);

        PasswordToggle.attach(etPassword);

        btnCycleAvatar.setOnClickListener(v -> {
            currentAvatar = (currentAvatar % 5) + 1;
            ivAvatarPreview.setImageResource(avatarDrawables[currentAvatar - 1]);
        });

        btnSubmitRegister.setOnClickListener(v -> submitRegistration());
        tvBackToLogin.setOnClickListener(v -> finish());
    }

    private void submitRegistration() {
        String username = etUsername.getText().toString().trim();
        String email = etEmail.getText().toString().trim();
        String password = etPassword.getText().toString().trim();
        String address = etAddress.getText().toString().trim();
        String ageStr = etAge.getText().toString().trim();

        if (TextUtils.isEmpty(username)) {
            etUsername.setError("Username is required");
            return;
        }
        if (TextUtils.isEmpty(email)) {
            etEmail.setError("Email is required");
            return;
        }
        if (TextUtils.isEmpty(password)) {
            etPassword.setError("Password is required");
            return;
        }

        int age = TextUtils.isEmpty(ageStr) ? 20 : Integer.parseInt(ageStr);
        String gender = "Male";
        int checkedId = rgGender.getCheckedRadioButtonId();
        if (checkedId == R.id.rbFemale) gender = "Female";
        else if (checkedId == R.id.rbOther) gender = "Other";

        // Save extended profile fields locally - the backend has no columns for these.
        dbHelper.registerUser(username, email, password, address, gender, age, currentAvatar);

        Map<String, String> body = new HashMap<>();
        body.put("username", username);
        body.put("email", email);
        body.put("password", password);

        btnSubmitRegister.setEnabled(false);

        ApiClient.get(this).signup(body).enqueue(new Callback<Map<String, Object>>() {
            @SuppressWarnings("unchecked")
            @Override
            public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                btnSubmitRegister.setEnabled(true);
                if (response.isSuccessful() && response.body() != null) {
                    String token = String.valueOf(response.body().get("access_token"));
                    saveSessionAndProceed(username, email, token);
                    Toast.makeText(RegisterActivity.this, "Account created", Toast.LENGTH_SHORT).show();
                } else {
                    String detail = parseErrorDetail(response);
                    Toast.makeText(RegisterActivity.this, detail != null ? detail : "Could not create account", Toast.LENGTH_LONG).show();
                }
            }

            @Override
            public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                btnSubmitRegister.setEnabled(true);
                // Server unreachable: proceed with the locally-saved profile only.
                saveSessionAndProceed(username, email, "offline_token");
                Toast.makeText(RegisterActivity.this, "Server unreachable - account saved offline only", Toast.LENGTH_LONG).show();
            }
        });
    }

    private String parseErrorDetail(Response<Map<String, Object>> response) {
        try {
            if (response.errorBody() != null) {
                String raw = response.errorBody().string();
                org.json.JSONObject obj = new org.json.JSONObject(raw);
                return obj.optString("detail", null);
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private void saveSessionAndProceed(String username, String email, String token) {
        SharedPreferences prefs = getSharedPreferences("rag_prefs", MODE_PRIVATE);
        prefs.edit()
                .putString("username", username)
                .putString("email", email)
                .putString("token", token)
                .putBoolean("is_guest", false)
                .putInt("avatar_id", currentAvatar)
                .apply();

        startActivity(new Intent(RegisterActivity.this, MainActivity.class));
        finish();
    }
}