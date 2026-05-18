#version 430 core

in vec3 v_color;
in vec2 v_texcoord;
in vec3 v_rgb;
in float v_alpha;
in vec2 v_view_size;
in float v_inv_depth;

out vec4 FragColor;

uniform sampler2D u_texture;

void main()
{
    vec2 uv = v_texcoord / v_inv_depth;
    vec4 texColor = texture(u_texture, uv);
    float t = 1 - (gl_FragCoord.y - 350.0) / 200.0;
    texColor.xyz = mix(vec3(100.0 / 255.0 / 2.0, 66.0 / 255.0 / 2.0, 47.0 / 255.0 / 2.0), texColor.xyz, vec3(t, t, t));
    texColor.xyz *= (gl_FragCoord.y - 100.0) / 300.0;
    texColor.xyz = mix(vec3(100.0 / 255.0 / 2.0, 66.0 / 255.0 / 2.0, 47.0 / 255.0 / 2.0), texColor.xyz, vec3(.6, .6, .6));
    FragColor = texColor * vec4(v_color * v_rgb, v_alpha);
}