#version 430 core

in vec3 v_rgb;
in float v_alpha;
in vec2 v_texcoord;

uniform sampler2D uTexture;

out vec4 FragColor;

void main()
{
    vec4 tex = texture(uTexture, v_texcoord);

    FragColor = vec4(
        tex.rgb * v_rgb,
        tex.a * v_alpha
    );
}