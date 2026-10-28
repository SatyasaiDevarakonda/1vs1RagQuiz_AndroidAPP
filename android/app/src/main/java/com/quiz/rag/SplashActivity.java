package com.quiz.rag;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.animation.AlphaAnimation;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

public class SplashActivity extends AppCompatActivity {

    private TextView tvSplashTitle;
    private ImageView ivSplashLogo;
    private final Handler handler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_splash);

        tvSplashTitle = findViewById(R.id.tvSplashTitle);
        ivSplashLogo = findViewById(R.id.ivSplashLogo);

        // Smooth pulse fade-in animation
        AlphaAnimation pulse = new AlphaAnimation(0.4f, 1.0f);
        pulse.setDuration(900);
        pulse.setRepeatMode(AlphaAnimation.REVERSE);
        pulse.setRepeatCount(1);
        ivSplashLogo.startAnimation(pulse);

        // Route after 2s
        handler.postDelayed(() -> {
            SharedPreferences prefs = getSharedPreferences("rag_prefs", MODE_PRIVATE);
            boolean isLoggedIn = prefs.contains("username");

            Intent intent;
            if (isLoggedIn) {
                intent = new Intent(SplashActivity.this, MainActivity.class);
            } else {
                intent = new Intent(SplashActivity.this, LoginActivity.class);
            }
            startActivity(intent);
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out);
            finish();
        }, 2000);
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        super.onDestroy();
    }
}