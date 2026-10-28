package com.quiz.rag;

import android.os.Bundle;

import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;

import com.google.android.material.bottomnavigation.BottomNavigationView;
import com.quiz.rag.fragments.HomeFragment;
import com.quiz.rag.fragments.LeaderboardFragment;
import com.quiz.rag.fragments.PlayFragment;
import com.quiz.rag.fragments.ProfileFragment;

/**
 * Lab Exp 11: BottomNavigationView with 4 Fragments: Home, Play, Leaderboard, Profile
 */
public class MainActivity extends AppCompatActivity {

    private BottomNavigationView nav;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        nav = findViewById(R.id.bottomNav);

        // Load HomeFragment by default, unless the caller asked for a specific tab
        // (e.g. ResultActivity's "Play again" button opens straight to Play).
        if (savedInstanceState == null) {
            if ("play".equals(getIntent().getStringExtra("openTab"))) {
                nav.setSelectedItemId(R.id.nav_play);
            } else {
                loadFragment(new HomeFragment());
            }
        }

        nav.setOnItemSelectedListener(item -> {
            Fragment f;
            int id = item.getItemId();
            if (id == R.id.nav_play) {
                f = new PlayFragment();
            } else if (id == R.id.nav_board) {
                f = new LeaderboardFragment();
            } else if (id == R.id.nav_profile) {
                f = new ProfileFragment();
            } else {
                f = new HomeFragment();
            }
            return loadFragment(f);
        });
    }

    private boolean loadFragment(Fragment fragment) {
        if (fragment != null) {
            getSupportFragmentManager().beginTransaction()
                    .replace(R.id.container, fragment)
                    .commit();
            return true;
        }
        return false;
    }

    /** Lets other fragments (e.g. Home's quick-start buttons) switch tabs. */
    public void openPlayTab() {
        nav.setSelectedItemId(R.id.nav_play);
    }
}