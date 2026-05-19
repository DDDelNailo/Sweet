#version 430 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_color;
layout(location = 2) in vec2 a_texcoord;

layout(location = 3) in vec3 iPos;
layout(location = 4) in vec3 iScale;
layout(location = 5) in vec3 iRot;
layout(location = 6) in vec2 iOffset;
layout(location = 7) in vec2 iUVOff;
layout(location = 8) in vec2 iUVScale;
layout(location = 9) in vec2 iView;
layout(location = 10) in vec3 iRgb;
layout(location = 11) in float iAlpha;

uniform mat4 uProjection;

out vec3 v_color;
out vec3 v_rgb;
out float v_alpha;
out vec2 v_texcoord;

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

    // scale in screen-space style units
    pos *= vec3(
        iScale.x * iView.y / iView.x / iView.x,
        iScale.y / iView.y,
        iScale.z
    );

    // rotation
    pos = rotX(iRot.x) * pos;
    pos = rotY(iRot.y) * pos;
    pos = rotZ(iRot.z) * pos;

    // translation
    pos += vec3(
        iPos.x / iView.x,
        iPos.y / iView.y,
        iPos.z
    );

    // REAL projection
    gl_Position = uProjection * vec4(pos, 1.0);

    // screen offset
    gl_Position.xy += vec2(
        iOffset.x / iView.x * 2.0,
        iOffset.y / iView.y * 2.0
    ) * gl_Position.w;
    
    // normal UVs
    v_texcoord =
        vec2(a_texcoord.x, 1.0 - a_texcoord.y)
        * iUVScale
        + iUVOff;

    v_color = a_color;
    v_rgb = iRgb;
    v_alpha = iAlpha;
}