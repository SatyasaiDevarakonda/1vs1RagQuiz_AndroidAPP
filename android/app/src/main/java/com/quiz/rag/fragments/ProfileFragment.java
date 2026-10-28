package com.quiz.rag.fragments;

import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.RadioGroup;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;

import com.quiz.rag.LoginActivity;
import com.quiz.rag.R;
import com.quiz.rag.db.DbHelper;
import com.quiz.rag.model.User;
import com.quiz.rag.net.ApiClient;

import java.util.Map;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * Lab Exp 2: Settings theme/background color picker
 * Lab Exp 5: 5-Avatar selector with Next cycling button
 */
public class ProfileFragment extends Fragment {

    private ImageView ivAvatar;
    private Button btnNextAvatar, btnLogout, btnSaveServerUrl, btnSaveProfileDetails;
    private TextView tvUsername, tvEmail, tvCurrentTheme;
    private TextView tvStatMatches, tvStatWins, tvStatScore;
    private ProgressBar progressStats;
    private EditText etServerUrl, etProfileAddress, etProfileAge;
    private RadioGroup rgProfileGender;

    private DbHelper dbHelper;
    private int currentAvatar = 1;
    private final int[] avatarDrawables = {
            R.drawable.ic_avatar_1,
            R.drawable.ic_avatar_2,
            R.drawable.ic_avatar_3,
            R.drawable.ic_avatar_4,
            R.drawable.ic_avatar_5
    };

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        View v = inflater.inflate(R.layout.fragment_profile, container, false);

        dbHelper = new DbHelper(requireContext());

        ivAvatar = v.findViewById(R.id.ivProfileAvatar);
        btnNextAvatar = v.findViewById(R.id.btnProfileNextAvatar);
        tvUsername = v.findViewById(R.id.tvProfileUsername);
        tvEmail = v.findViewById(R.id.tvProfileEmail);
        tvCurrentTheme = v.findViewById(R.id.tvCurrentTheme);
        btnLogout = v.findViewById(R.id.btnLogout);
        etServerUrl = v.findViewById(R.id.etServerUrl);
        btnSaveServerUrl = v.findViewById(R.id.btnSaveServerUrl);
        tvStatMatches = v.findViewById(R.id.tvStatMatches);
        tvStatWins = v.findViewById(R.id.tvStatWins);
        tvStatScore = v.findViewById(R.id.tvStatScore);
        progressStats = v.findViewById(R.id.progressStats);
        etProfileAddress = v.findViewById(R.id.etProfileAddress);
        etProfileAge = v.findViewById(R.id.etProfileAge);
        rgProfileGender = v.findViewById(R.id.rgProfileGender);
        btnSaveProfileDetails = v.findViewById(R.id.btnSaveProfileDetails);

        SharedPreferences prefs = requireContext().getSharedPreferences("rag_prefs", Context.MODE_PRIVATE);
        String username = prefs.getString("username", "Player");
        tvUsername.setText(username);
        tvEmail.setText(prefs.getString("email", ""));
        currentAvatar = prefs.getInt("avatar_id", 1);
        updateAvatarDisplay();

        etServerUrl.setText(ApiClient.getSavedBaseUrl(requireContext()));
        loadStats();
        loadProfileDetails(username);

        // Exp 5: Next Avatar Button
        btnNextAvatar.setOnClickListener(view -> {
            currentAvatar = (currentAvatar % 5) + 1;
            prefs.edit().putInt("avatar_id", currentAvatar).apply();
            updateAvatarDisplay();
        });

        // Exp 2: Settings Theme & Background Color Picker
        setupThemePicker(v, prefs);

        btnSaveProfileDetails.setOnClickListener(view -> saveProfileDetails(username));

        // Server URL config for Render or local
        btnSaveServerUrl.setOnClickListener(view -> {
            String url = etServerUrl.getText().toString().trim();
            if (!url.isEmpty()) {
                ApiClient.setSavedBaseUrl(requireContext(), url);
                Toast.makeText(getContext(), "Backend URL updated!", Toast.LENGTH_SHORT).show();
            }
        });

        // Logout
        btnLogout.setOnClickListener(view -> {
            prefs.edit().remove("username").remove("token").apply();
            startActivity(new Intent(getActivity(), LoginActivity.class));
            requireActivity().finish();
        });

        return v;
    }

    private void loadProfileDetails(String username) {
        User user = dbHelper.getUserProfile(username);
        if (user == null) return;

        if (!TextUtils.isEmpty(user.getAddress())) {
            etProfileAddress.setText(user.getAddress());
        }
        if (user.getAge() > 0) {
            etProfileAge.setText(String.valueOf(user.getAge()));
        }
        if ("Female".equalsIgnoreCase(user.getGender())) {
            rgProfileGender.check(R.id.rbProfileFemale);
        } else if ("Other".equalsIgnoreCase(user.getGender())) {
            rgProfileGender.check(R.id.rbProfileOther);
        }
    }

    private void saveProfileDetails(String username) {
        String address = etProfileAddress.getText().toString().trim();
        int age = 0;
        try {
            age = Integer.parseInt(etProfileAge.getText().toString().trim());
        } catch (NumberFormatException ignored) {
        }

        String gender = "Male";
        int checkedId = rgProfileGender.getCheckedRadioButtonId();
        if (checkedId == R.id.rbProfileFemale) gender = "Female";
        else if (checkedId == R.id.rbProfileOther) gender = "Other";

        dbHelper.upsertProfileDetails(username, address, gender, age);
        Toast.makeText(getContext(), "Saved", Toast.LENGTH_SHORT).show();
    }

    @SuppressWarnings("unchecked")
    private void loadStats() {
        SharedPreferences prefs = requireContext().getSharedPreferences("rag_prefs", Context.MODE_PRIVATE);
        if (prefs.getBoolean("is_guest", false)) {
            return; // Guests have no persisted stats on the backend
        }

        progressStats.setVisibility(View.VISIBLE);
        String bearer = ApiClient.bearer(requireContext());
        ApiClient.get(requireContext()).me(bearer).enqueue(new Callback<Map<String, Object>>() {
            @Override
            public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                if (getView() == null) return;
                progressStats.setVisibility(View.GONE);
                if (!response.isSuccessful() || response.body() == null) return;
                Map<String, Object> user = (Map<String, Object>) response.body().get("user");
                if (user == null) return;
                tvStatMatches.setText(String.valueOf(asInt(user.get("games_played"))));
                tvStatWins.setText(String.valueOf(asInt(user.get("games_won"))));
                tvStatScore.setText(String.valueOf(asInt(user.get("total_score"))));
            }

            @Override
            public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                if (getView() == null) return;
                progressStats.setVisibility(View.GONE);
                // Keep placeholder zeros if the server is unreachable
            }
        });
    }

    /** Gson parses JSON numbers in a Map<String,Object> as Double - normalize before display. */
    private static int asInt(Object value) {
        if (value instanceof Number) return ((Number) value).intValue();
        return 0;
    }

    private void updateAvatarDisplay() {
        int index = Math.max(0, Math.min(4, currentAvatar - 1));
        ivAvatar.setImageResource(avatarDrawables[index]);
    }

    private void setupThemePicker(View root, SharedPreferences prefs) {
        View themeCyber = root.findViewById(R.id.themeCyber);
        View themeViolet = root.findViewById(R.id.themeViolet);
        View themeTeal = root.findViewById(R.id.themeTeal);
        View themeSunset = root.findViewById(R.id.themeSunset);
        View themeLight = root.findViewById(R.id.themeLight);

        String active = prefs.getString("theme_name", "Neutral");
        tvCurrentTheme.setText(active);

        themeCyber.setOnClickListener(v -> applyTheme("Neutral", "#F6F7F9", prefs));
        themeViolet.setOnClickListener(v -> applyTheme("Warm", "#FAF8F5", prefs));
        themeTeal.setOnClickListener(v -> applyTheme("Cool", "#F3F6FB", prefs));
        themeSunset.setOnClickListener(v -> applyTheme("Mint", "#F2F8F5", prefs));
        themeLight.setOnClickListener(v -> applyTheme("Slate", "#EEF0F3", prefs));
    }

    private void applyTheme(String name, String hexColor, SharedPreferences prefs) {
        prefs.edit().putString("theme_name", name).putString("theme_color", hexColor).apply();
        tvCurrentTheme.setText(name);
        if (getView() != null) {
            getView().setBackgroundColor(Color.parseColor(hexColor));
        }
    }
}
