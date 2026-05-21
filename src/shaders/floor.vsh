#version 430 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_color;
layout(location = 2) in vec2 a_texcoord;

layout(location = 3) in vec2 iPos;
layout(location = 4) in vec2 iScale;
layout(location = 5) in vec2 iRot;
layout(location = 6) in vec2 iUVOff;
layout(location = 7) in vec2 iUVScale;
layout(location = 8) in vec3 iRgb;
layout(location = 9) in float iAlpha;

layout(location = 10) in vec2 iView;
layout(location = 11) in vec3 iNPos;
layout(location = 12) in vec3 iNScale;
layout(location = 13) in vec3 iNRot;

// (0,0,0) = centered on screen
// scale = (1,1) = fills the entire screen
// position.x = 1 = move by exactly one screen width
// position.y = 1 = move by exactly one screen height
// z = 0 = normal depth
// positive z = farther away
// negative z = closer to camera

out vec3 v_color;
out vec3 v_rgb;
out float v_alpha;
out vec2 v_view_size;
out vec2 v_texcoord;
out float v_inv_depth;

mat3 rotX(float a)
{
    float s = sin(a);
    float c = cos(a);

    return mat3(
        1, 0, 0,
        0, c,-s,
        0, s, c
    );
}

mat3 rotY(float a)
{
    float s = sin(a);
    float c = cos(a);

    return mat3(
         c, 0, s,
         0, 1, 0,
        -s, 0, c
    );
}

mat3 rotZ(float a)
{
    float s = sin(a);
    float c = cos(a);

    return mat3(
        c,-s,0,
        s, c,0,
        0, 0,1
    );
}

void main()
{
    vec3 pos = a_position;

    // ======================
    // SCALE
    // ======================

    // pos *= iNScale;
    pos *= vec3(iNScale.x * iScale.x / iView.x * 1.001, iNScale.y * iScale.y / iView.y * 1.001, iNScale.z);

    // ======================
    // ROTATION
    // ======================

    pos = rotX(iNRot.x) * pos;
    pos = rotY(iNRot.y) * pos;
    pos = rotZ(iNRot.z) * pos;

    // ======================
    // TRANSLATION
    // ======================

    // pos += iNPos;
    pos += vec3(iNPos.x + iPos.x / iView.x, iNPos.y, iNPos.z);

    // ======================
    // PERSPECTIVE
    // ======================

    // Camera distance from z=0 plane
    float cameraDist = 1.0;

    // Prevent division explosion
    float depth = max(0.001, cameraDist + pos.z);

    // Perspective divide manually
    vec2 projected = pos.xy / depth;

    // Convert "screen units" to clip space
    projected *= 2.0;

    gl_Position = vec4(
        projected,
        pos.z,
        1.0
    );

    vec2 uv = a_texcoord * iUVScale + iUVOff;

    v_inv_depth = 1.0 / depth;
    v_texcoord = uv * v_inv_depth;

    gl_Position.xy += vec2(0, -iPos.y / iView.y * 2) * gl_Position.w;

    v_color = a_color;
    v_rgb = iRgb;
    v_alpha = iAlpha;
    v_view_size = iView;
}