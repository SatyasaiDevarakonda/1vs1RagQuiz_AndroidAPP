package com.quiz.rag.util;

import android.text.InputType;
import android.view.MotionEvent;
import android.widget.EditText;

import com.quiz.rag.R;

/**
 * Makes the eye icon set as an EditText's drawableEnd toggle password
 * visibility on tap. Attach once per password field.
 */
public final class PasswordToggle {

    private PasswordToggle() {
    }

    public static void attach(EditText field) {
        field.setOnTouchListener((v, event) -> {
            if (event.getAction() != MotionEvent.ACTION_UP) return false;

            android.graphics.drawable.Drawable end = field.getCompoundDrawables()[2];
            if (end == null) return false;

            // Only react to taps within the icon's bounds, not the whole field.
            boolean tappedIcon = event.getRawX() >= (field.getRight() - end.getBounds().width() - field.getPaddingEnd());
            if (!tappedIcon) return false;

            boolean isVisible = field.getInputType() == (InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD);
            if (isVisible) {
                field.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
                field.setCompoundDrawablesWithIntrinsicBounds(0, 0, R.drawable.ic_eye, 0);
            } else {
                field.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD);
                field.setCompoundDrawablesWithIntrinsicBounds(0, 0, R.drawable.ic_eye_off, 0);
            }
            field.setSelection(field.getText().length());
            return true;
        });
    }
}
